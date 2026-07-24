/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

const EXACT_LABEL = "A la mano";

publicWidget.registry.MdBentoInteractions = publicWidget.Widget.extend({
    selector: "body",

    start() {
        const result = this._super(...arguments);
        // Primero: antes que cualquier otra cosa (ver por que en el
        // comentario del metodo) — corre lo antes posible en el ciclo de
        // vida del widget, para ganarle a la medicion de altura del grid
        // masonry nativo de Odoo.
        this._forceEagerProductImages();
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

    // FIX (bug real, tienda): el grid masonry NATIVO de Odoo 19
    // (website_sale, --o-wsale-products-grid-product-col-height) mide la
    // altura real de cada tarjeta via JS para asignarle su row-span en el
    // CSS Grid. Las imagenes del grid nativo traen loading="lazy" — para
    // tarjetas fuera del viewport inicial, esa medicion ocurre ANTES de
    // que la imagen cargue, asi que la tarjeta queda con una altura
    // calculada minima (~28px). Como la tarjeta tiene overflow:hidden, el
    // resto del contenido (nombre, precio, badge "A la mano") se recorta
    // y la tarjeta se ve completamente en blanco aunque su HTML este
    // completo — confirmado en vivo con Playwright, no se ve en el
    // servidor (no hay traceback) porque es puramente un problema de
    // timing/CSS en el navegador. No re-mide despues de que la imagen
    // carga tarde, asi que el problema no se autocorrige.
    //
    // Fix: forzar loading="eager" en las imagenes del grid apenas el
    // widget arranca, para que ya esten cargadas (o cargando) cuando
    // Odoo mida las alturas. No se toca el mecanismo de medicion nativo
    // ni el core — solo se le quita el gatillo (lazy) que lo desincroniza.
    _forceEagerProductImages() {
        this.el.querySelectorAll(
            ".o_wsale_products_grid_table img[loading='lazy'], .oe_product_image_img[loading='lazy'], .oe_product_image_img_secondary[loading='lazy']"
        ).forEach((img) => {
            img.loading = "eager";
        });
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
