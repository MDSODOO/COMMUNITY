/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

// ════════════════════════════════════════════════════════════════════════
// RaffleWheel — el backend decide al ganador ANTES de animar
// (raffle.campaign.action_draw_winner usa random.SystemRandom en el
// servidor). Este componente nunca decide el resultado, solo lo revela.
//
// Reproduce el prototipo de diseño "Ruleta Sorteo" (marquesina con luces
// chase, reel de caracteres estilo tómbola, mascota Dr. Q con poses
// aleatorias en dos momentos distintos, confetti físico) adaptado para
// soportar múltiples premios: la campaña expone una cola de premios
// pendientes (get_pending_prizes, ya ordenada por secuencia) y el
// componente la consume uno a la vez — gira, el servidor guarda el
// ganador de ESE premio en raffle.prize, se revela, y si quedan premios
// se ofrece "Revelar al siguiente ganador" para repetir el ciclo sin
// recargar la página.
//
// El reel anima carácter por carácter (no folio completo): cada folio se
// descompone en celdas (letras del código de campaña, origen R/BP,
// consecutivo numérico) que ciclan caracteres al azar y frenan en el
// caracter real ya decidido por el servidor — igual que una tómbola.
// ════════════════════════════════════════════════════════════════════════

const DIGITS = "0123456789";
const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
const ORIGIN_CHARS = "RBP";
const ASSET_BASE = "/mds_raffle_campaign/static/src/img/";

// "mascota-point.png" queda fuera a propósito: el archivo entregado en el
// bundle de diseño no es una pose de la mascota (es un teléfono suelto,
// mal etiquetado) — el README original ya lo marcaba como "unused/optional".
const SPIN_POSES = [
    { img: "mascota-shrug.png", line: "A ver, a ver… ¡no hago trampa! 😅" },
    { img: "mascota-wave.png", line: "¡Mucha suerte a todos! 🍀" },
];
const CONGRATS_POSES = [
    { img: "mascota-thumbsup.png", line: "¡Felicidades, ganador/a! 🎉" },
    { img: "mascota-peace2.png", line: "¡Eso es todo, disfrútalo! ✌️" },
];

function pick(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

function cellsFromFolio(folio) {
    const parts = folio.split("-");
    if (parts.length !== 3) {
        // formato inesperado: se anima caracter por caracter sin distinguir
        // segmentos (fallback defensivo, no debería ocurrir en producción)
        return folio.split("").map((ch) => (
            /[0-9]/.test(ch) ? { type: "digit", target: ch } : { type: "letter", target: ch }
        ));
    }
    const [prefix, origin, consecutive] = parts;
    const cells = [];
    prefix.split("").forEach((ch) => cells.push({ type: "letter", target: ch }));
    cells.push({ type: "literal", value: "-" });
    origin.split("").forEach((ch) => cells.push({ type: "origin", target: ch }));
    cells.push({ type: "literal", value: "-" });
    consecutive.split("").forEach((ch) => cells.push({ type: "digit", target: ch }));
    return cells;
}

function alphabetFor(type) {
    if (type === "digit") return DIGITS;
    if (type === "origin") return ORIGIN_CHARS;
    return LETTERS;
}

function randChar(alphabet) {
    return alphabet[Math.floor(Math.random() * alphabet.length)];
}

function buildStripChars(type, target, len) {
    const alphabet = alphabetFor(type);
    const chars = [];
    for (let i = 0; i < len; i++) {
        chars.push(randChar(alphabet));
    }
    chars.push(target);
    return chars;
}

export class RaffleWheel extends Component {
    static template = "mds_raffle_campaign.RaffleWheel";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.campaignId = this.props.action.params.campaign_id;

        const params = this.props.action.params || {};
        this.mascotEnabled = params.mascot_enabled !== false;
        this.spinSpeed = params.spin_speed || 1;
        this.confettiEnabled = params.confetti !== false;
        this.reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        this.marqueeRef = useRef("marquee");
        this.reelWindowRef = useRef("reelWindow");
        this.bulbsTopRef = useRef("bulbsTop");
        this.bulbsBottomRef = useRef("bulbsBottom");
        this.mascotRef = useRef("mascot");
        this.mascotBubbleRef = useRef("mascotBubble");
        this.mascotImgRef = useRef("mascotImg");
        this.confettiRef = useRef("confetti");

        this.cellEls = [];
        this.spinning = false;
        this.confettiParticles = [];
        this.confettiRafId = null;
        this.confettiStart = 0;
        this.tickets = [];
        this.prizeQueue = [];

        this.state = useState({
            campaignName: "",
            ticketCount: 0,
            currentPrize: null,
            spinBtnLabel: "Girar la suerte",
            spinBtnDisabled: false,
            spinHint: "Un folio, un ganador — el resultado no cambia entre giros.",
            winner: null,
            history: [],
            done: false,
        });

        this._resizeConfetti = () => {
            const canvas = this.confettiRef.el;
            if (canvas) {
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
            }
        };

        onWillStart(async () => {
            const [campaign] = await this.orm.read(
                "raffle.campaign", [this.campaignId], ["name"]
            );
            const [tickets, prizes] = await Promise.all([
                this.orm.searchRead(
                    "raffle.ticket",
                    [["campaign_id", "=", this.campaignId], ["state", "=", "valid"]],
                    ["name", "partner_id", "origin_type"]
                ),
                this.orm.call("raffle.campaign", "get_pending_prizes", [this.campaignId]),
            ]);
            this.tickets = tickets;
            this.prizeQueue = prizes;
            this.state.campaignName = campaign.name;
            this.state.ticketCount = tickets.length;
            this.state.currentPrize = prizes[0] || null;
            this.state.done = !prizes.length;
        });

        onMounted(() => {
            this._buildBulbs(this.bulbsTopRef.el, 16);
            this._buildBulbs(this.bulbsBottomRef.el, 16);
            window.addEventListener("resize", this._resizeConfetti);
            this._resizeConfetti();
            // Si la campaña ya no tiene premios pendientes al ABRIR la ruleta
            // (no solo después de un giro), la action-zone del template no
            // pinta nada cuando hay mascota habilitada (el done-banner solo
            // aparece con !mascotEnabled/reducedMotion — ver raffle_wheel.xml).
            // Sin este disparo, la página se ve vacía debajo del marquee.
            // Replica el mismo cierre que onSpinClick corre tras el último
            // giro: mascota final fija + su bocadillo con el aviso de cierre.
            if (this.state.done) {
                setTimeout(() => this._runFinalCongrats(), 250);
            }
        });

        onWillUnmount(() => {
            window.removeEventListener("resize", this._resizeConfetti);
            if (this.confettiRafId) {
                cancelAnimationFrame(this.confettiRafId);
            }
        });
    }

    _buildBulbs(container, count) {
        if (!container) return;
        container.innerHTML = "";
        for (let i = 0; i < count; i++) {
            const bulb = document.createElement("div");
            bulb.className = "o_raffle_bulb";
            bulb.style.animationDelay = (i * 0.09) + "s";
            container.appendChild(bulb);
        }
    }

    _renderCells(folio) {
        const reelWindow = this.reelWindowRef.el;
        if (!reelWindow) return;
        reelWindow.innerHTML = "";
        const track = document.createElement("div");
        track.className = "o_raffle_reel_track";
        reelWindow.appendChild(track);

        this.cellEls = [];
        const stripLen = this.reducedMotion ? 6 : 30;
        cellsFromFolio(folio).forEach((cfg) => {
            if (cfg.type === "literal") {
                const cell = document.createElement("div");
                cell.className = "o_raffle_cell_literal";
                cell.textContent = cfg.value;
                track.appendChild(cell);
                return;
            }
            const cell = document.createElement("div");
            cell.className = "o_raffle_cell";
            const strip = document.createElement("div");
            strip.className = "o_raffle_cell_strip";
            const chars = buildStripChars(cfg.type, cfg.target, stripLen);
            chars.forEach((ch) => {
                const charEl = document.createElement("div");
                charEl.className = "o_raffle_cell_char";
                charEl.textContent = ch;
                strip.appendChild(charEl);
            });
            cell.appendChild(strip);
            track.appendChild(cell);
            this.cellEls.push({ el: cell, stripEl: strip, restLen: chars.length });
        });

        // Códigos de campaña más largos generan más celdas de las que caben
        // a tamaño completo en la marquesina — en vez de envolver a una
        // segunda línea (rompe el efecto tómbola), se encoge el track
        // completo de forma proporcional para que siempre quede en una sola
        // fila, sin importar la longitud del folio.
        track.style.transform = "scale(1)";
        const availableWidth = reelWindow.clientWidth;
        const neededWidth = track.scrollWidth;
        if (neededWidth > availableWidth && availableWidth > 0) {
            const scale = availableWidth / neededWidth;
            track.style.transform = `scale(${scale})`;
        }
    }

    _runMascot(pose) {
        if (!this.mascotEnabled || this.reducedMotion) return;
        const mascot = this.mascotRef.el;
        const bubble = this.mascotBubbleRef.el;
        const img = this.mascotImgRef.el;
        if (!mascot || !bubble || !img) return;

        img.src = ASSET_BASE + pose.img;
        bubble.textContent = pose.line;
        mascot.style.animation = "mds_raffle_mascotIn .75s ease-out forwards";
        mascot.style.opacity = "1";
        setTimeout(() => {
            bubble.style.opacity = "1";
            bubble.style.transform = "translateX(-50%) scale(1)";
        }, 420);
        setTimeout(() => {
            mascot.style.animation = "mds_raffle_armPull .9s ease-in-out";
        }, 700);
        setTimeout(() => {
            bubble.style.opacity = "0";
            bubble.style.transform = "translateX(-50%) scale(.85)";
        }, 2100);
        setTimeout(() => {
            mascot.style.animation = "mds_raffle_mascotOut .65s ease-in forwards";
        }, 2450);
    }

    _runCongrats(pose) {
        if (!this.mascotEnabled || this.reducedMotion) return;
        const mascot = this.mascotRef.el;
        const bubble = this.mascotBubbleRef.el;
        const img = this.mascotImgRef.el;
        if (!mascot || !bubble || !img) return;

        img.src = ASSET_BASE + pose.img;
        bubble.textContent = pose.line;
        mascot.style.animation = "mds_raffle_mascotIn .6s cubic-bezier(.2,.9,.3,1.3) forwards";
        mascot.style.opacity = "1";
        setTimeout(() => {
            bubble.style.opacity = "1";
            bubble.style.transform = "translateX(-50%) scale(1)";
        }, 260);
        setTimeout(() => {
            bubble.style.opacity = "0";
            bubble.style.transform = "translateX(-50%) scale(.85)";
        }, 2600);
        setTimeout(() => {
            mascot.style.animation = "mds_raffle_mascotOut .5s ease-in forwards";
        }, 2950);
    }

    // Cuando ya no quedan premios, la mascota no vuelve a desvanecerse
    // (mascotOut): se queda parada y fija del lado derecho de la ruleta,
    // con el mensaje de cierre en su propio bocadillo — el bocadillo
    // "absorbe" el aviso de fin de sorteo en vez de mostrarlo aparte.
    _runFinalCongrats() {
        if (!this.mascotEnabled || this.reducedMotion) return;
        const mascot = this.mascotRef.el;
        const bubble = this.mascotBubbleRef.el;
        const img = this.mascotImgRef.el;
        if (!mascot || !bubble || !img) return;

        const pose = pick(CONGRATS_POSES);
        img.src = ASSET_BASE + pose.img;
        bubble.textContent = "¡Todos los premios ya tienen ganador! 🎉";
        mascot.style.animation = "mds_raffle_mascotFinal .7s cubic-bezier(.2,.9,.3,1.3) forwards";
        mascot.style.opacity = "1";
        setTimeout(() => {
            bubble.style.opacity = "1";
            bubble.style.transform = "translateX(-50%) scale(1)";
        }, 320);
    }

    prizeImageUrl(prizeId) {
        return `/web/image/raffle.prize/${prizeId}/image`;
    }

    onImageError(ev) {
        ev.target.style.display = "none";
    }

    async onSpinClick() {
        const prize = this.state.currentPrize;
        if (this.spinning || !prize) {
            return;
        }
        this.spinning = true;
        this.state.winner = null;
        this.state.spinBtnDisabled = true;
        this.state.spinBtnLabel = "Girando…";
        this.state.spinHint = "Revelando el folio ya asignado por el servidor…";
        this._runMascot(pick(SPIN_POSES));

        const winnerId = await this.orm.call(
            "raffle.campaign", "action_draw_winner", [this.campaignId, prize.id]
        );
        const [winnerTicket] = await this.orm.read(
            "raffle.ticket", [winnerId], ["name", "partner_id", "origin_type"]
        );

        this._spinReelTo(winnerTicket, prize);
    }

    _spinReelTo(winnerTicket, prize) {
        this._renderCells(winnerTicket.name);
        this.cellEls.forEach((c) => {
            c.stripEl.style.transition = "none";
            c.stripEl.style.transform = "translateY(0px)";
        });
        // fuerza reflow: sin esto el salto a transform inicial también se anima
        void this.reelWindowRef.el.offsetHeight;

        let maxDuration = 0;
        const baseDuration = (this.reducedMotion ? 0.45 : 1.7) / this.spinSpeed;
        const step = (this.reducedMotion ? 0.05 : 0.24) / this.spinSpeed;

        this.cellEls.forEach((c, i) => {
            // offsetHeight (no getBoundingClientRect): el track puede tener
            // un scale() aplicado por _renderCells, y offsetHeight ignora
            // transforms — necesitamos la altura real pre-escala, porque el
            // translateY del strip vive en el sistema de coordenadas local
            // del track, antes de que el scale del padre lo visualice más chico.
            const cellHeight = c.el.offsetHeight;
            const distance = (c.restLen - 1) * cellHeight;
            const duration = baseDuration + i * step + Math.random() * 0.12;
            maxDuration = Math.max(maxDuration, duration);
            c.stripEl.style.transition = `transform ${duration.toFixed(2)}s cubic-bezier(0.13,0.82,0.24,1)`;
            requestAnimationFrame(() => {
                c.stripEl.style.transform = `translateY(-${distance}px)`;
            });
            setTimeout(() => {
                c.el.classList.add("o_raffle_cell_locked");
                c.el.style.animation = "mds_raffle_lockPulse .5s ease-out";
            }, duration * 1000);
        });

        setTimeout(() => this._reveal(winnerTicket, prize), maxDuration * 1000 + 200);
    }

    _reveal(winnerTicket, prize) {
        this.spinning = false;
        const originLabel = winnerTicket.origin_type === "online_b2b" ? "Folio B2B en línea" : "Folio físico";
        const winner = {
            prize,
            folio: winnerTicket.name,
            name: winnerTicket.partner_id[1],
            meta: `${originLabel} · sorteo del ${new Date().toLocaleDateString("es-MX")}`,
        };

        this.state.spinBtnDisabled = false;
        this.state.spinHint = "Un folio, un ganador — el resultado no cambia entre giros.";
        this.state.winner = winner;
        this.state.history.push(winner);

        this.tickets = this.tickets.filter((t) => t.id !== winnerTicket.id);
        this.prizeQueue = this.prizeQueue.filter((p) => p.id !== prize.id);
        this.state.currentPrize = this.prizeQueue[0] || null;
        this.state.ticketCount = this.tickets.length;
        this.state.spinBtnLabel = this.state.currentPrize ? "Revelar al siguiente ganador" : "Girar de nuevo";
        this.state.done = !this.state.currentPrize;

        if (this.marqueeRef.el) {
            this.marqueeRef.el.animate(
                [
                    { boxShadow: "0 26px 54px -18px rgba(10,60,80,.35)" },
                    { boxShadow: "0 26px 64px -12px rgba(151,215,0,.4)" },
                    { boxShadow: "0 26px 54px -18px rgba(10,60,80,.35)" },
                ],
                { duration: 900, easing: "ease-out" }
            );
        }
        if (!this.reducedMotion && this.confettiEnabled) {
            this._confettiBurst();
        }
        if (this.state.done) {
            setTimeout(() => this._runFinalCongrats(), 250);
        } else {
            setTimeout(() => this._runCongrats(pick(CONGRATS_POSES)), 250);
        }
    }

    _confettiBurst() {
        const canvas = this.confettiRef.el;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        // Paleta Quifamesa (Manual de marca 2026): navy, acero y los dos
        // azules claros del degradado de marquesina — igual que el
        // confettiBurst() del artifact "Quifamesa Sorteo" aprobado.
        const colors = ["#1B365D", "#285780", "#5E8AB4", "#7D9CC0"];
        const originX = window.innerWidth / 2;
        const originY = Math.min(window.innerHeight * 0.42, 340);

        this.confettiParticles = [];
        for (let i = 0; i < 130; i++) {
            const angle = Math.random() * Math.PI + Math.PI;
            const speed = 4 + Math.random() * 7;
            this.confettiParticles.push({
                x: originX + (Math.random() - 0.5) * 160,
                y: originY,
                vx: Math.cos(angle) * speed * 0.6 + (Math.random() - 0.5) * 3,
                vy: Math.sin(angle) * speed - 4,
                size: 4 + Math.random() * 5,
                color: colors[i % colors.length],
                rot: Math.random() * Math.PI * 2,
                vrot: (Math.random() - 0.5) * 0.3,
                shape: Math.random() > 0.5 ? "rect" : "circle",
            });
        }
        this.confettiStart = performance.now();
        if (this.confettiRafId) {
            cancelAnimationFrame(this.confettiRafId);
        }

        const tick = (now) => {
            const elapsed = now - this.confettiStart;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            const gravity = 0.14;
            let alive = false;
            this.confettiParticles.forEach((p) => {
                p.vy += gravity;
                p.x += p.vx;
                p.y += p.vy;
                p.rot += p.vrot;
                const fade = Math.max(0, 1 - elapsed / 2600);
                if (fade <= 0 || p.y > canvas.height + 20) return;
                alive = true;
                ctx.save();
                ctx.globalAlpha = fade;
                ctx.translate(p.x, p.y);
                ctx.rotate(p.rot);
                ctx.fillStyle = p.color;
                if (p.shape === "rect") {
                    ctx.fillRect(-p.size / 2, -p.size / 3, p.size, p.size * 0.66);
                } else {
                    ctx.beginPath();
                    ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
                    ctx.fill();
                }
                ctx.restore();
            });
            if (alive && elapsed < 3200) {
                this.confettiRafId = requestAnimationFrame(tick);
            } else {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                this.confettiRafId = null;
            }
        };
        this.confettiRafId = requestAnimationFrame(tick);
    }
}

registry.category("actions").add("mds_raffle_wheel", RaffleWheel);
