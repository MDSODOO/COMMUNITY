/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

const EXACT_LABEL = "A la mano";

publicWidget.registry.MdBentoInteractions = publicWidget.Widget.extend({
    selector: "body",

    start() {
        const result = this._super(...arguments);
        this._setupReveal();
        this._setupMarqueePause();
        this._setupCardTilt();
        this._normalizeLabels();
        this._observer = new MutationObserver(() => this._normalizeLabels());
        this._observer.observe(this.el, { childList: true, subtree: true });
        return result;
    },

    destroy() {
        this._intersectionObserver?.disconnect();
        this._observer?.disconnect();
        (this._tiltCleanups || []).forEach((fn) => fn());
        this._super(...arguments);
    },

    _setupReveal() {
        const items = this.el.querySelectorAll(".md-bento-card, .md-service-tile, .md-logo-tile");
        if (!("IntersectionObserver" in window)) {
            items.forEach((item) => item.classList.add("is-visible"));
            return;
        }
        this._intersectionObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    this._intersectionObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });
        items.forEach((item) => {
            item.classList.add("md-reveal");
            this._intersectionObserver.observe(item);
        });
    },

    _setupMarqueePause() {
        this.el.querySelectorAll("[data-md-marquee]").forEach((marquee) => {
            marquee.addEventListener("mouseenter", () => marquee.classList.add("is-paused"));
            marquee.addEventListener("mouseleave", () => marquee.classList.remove("is-paused"));
            marquee.addEventListener("focusin", () => marquee.classList.add("is-paused"));
            marquee.addEventListener("focusout", () => marquee.classList.remove("is-paused"));
        });
    },

    _normalizeLabels() {
        // Regla de negocio: el badge debe decir "A la mano" (nunca otra palabra).
        this.el.querySelectorAll(".o_sqty_stock .o_sqty_label").forEach((label) => {
            if (!label.textContent.trim().startsWith(EXACT_LABEL)) {
                label.textContent = `${EXACT_LABEL}:`;
            }
        });
    },

    // Escenario 4 — Tilt 3D / parallax suave de la imagen al mover el cursor.
    _setupCardTilt() {
        this._tiltCleanups = [];
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            return;
        }
        if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
            return;
        }
        const MAX_DEG = 6;
        this.el.querySelectorAll(".md-shop .md-product-card").forEach((card) => {
            const media = card.querySelector(".md-product-media");
            if (!media) {
                return;
            }
            const onMove = (ev) => {
                const rect = card.getBoundingClientRect();
                const px = (ev.clientX - rect.left) / rect.width - 0.5;
                const py = (ev.clientY - rect.top) / rect.height - 0.5;
                media.style.transform =
                    `perspective(620px) rotateX(${(-py * MAX_DEG).toFixed(2)}deg) ` +
                    `rotateY(${(px * MAX_DEG).toFixed(2)}deg)`;
            };
            const onLeave = () => { media.style.transform = ""; };
            card.addEventListener("pointermove", onMove);
            card.addEventListener("pointerleave", onLeave);
            this._tiltCleanups.push(() => {
                card.removeEventListener("pointermove", onMove);
                card.removeEventListener("pointerleave", onLeave);
            });
        });
    },
});
