/** @odoo-module **/

// Fase 2.2 · Off-canvas drawer de filtros en móvil (<992px).
// Inyecta overlay y FAB "Filtros" cuando el viewport es estrecho;
// los destruye al redimensionar a escritorio para no interferir con
// el layout nativo de columnas de Odoo.

import publicWidget from "@web/legacy/js/public/public_widget";

const BP_DRAWER = 992;

publicWidget.registry.MdShopDrawer = publicWidget.Widget.extend({
    selector: "body.md-route-shop",

    start() {
        this._isMobile = () => window.innerWidth < BP_DRAWER;
        this._overlay = null;
        this._fab = null;
        this._sidebar = null;

        if (this._isMobile()) {
            this._setupDrawer();
        }

        this._onResize = this._debounce(this._handleResize.bind(this), 120);
        window.addEventListener("resize", this._onResize, { passive: true });
        return this._super(...arguments);
    },

    // ── Inicialización ────────────────────────────────────────────────

    _setupDrawer() {
        this._sidebar = this.el.querySelector(
            ".o_wsale_products_grid_before_rail, .o_wsale_sidebar"
        );
        if (!this._sidebar) return;

        if (!this.el.querySelector(".md-shop-drawer-overlay")) {
            this._overlay = document.createElement("div");
            this._overlay.className = "md-shop-drawer-overlay";
            this._overlay.setAttribute("aria-hidden", "true");
            this._overlay.addEventListener("click", () => this._closeDrawer());
            this.el.appendChild(this._overlay);
        } else {
            this._overlay = this.el.querySelector(".md-shop-drawer-overlay");
        }

        if (!this.el.querySelector(".md-filter-fab")) {
            this._fab = document.createElement("button");
            this._fab.className = "md-filter-fab";
            this._fab.type = "button";
            this._fab.setAttribute("aria-label", "Mostrar filtros");
            this._fab.innerHTML = '<i class="fa fa-sliders" aria-hidden="true"></i>';
            this._fab.addEventListener("click", () => this._toggleDrawer());
            this.el.appendChild(this._fab);
        } else {
            this._fab = this.el.querySelector(".md-filter-fab");
        }
    },

    _teardownDrawer() {
        this._closeDrawer();
        this._overlay?.remove();
        this._fab?.remove();
        this._overlay = null;
        this._fab = null;
    },

    // ── Abrir / cerrar ────────────────────────────────────────────────

    _toggleDrawer() {
        const isOpen = this._sidebar?.classList.contains("is-open");
        isOpen ? this._closeDrawer() : this._openDrawer();
    },

    _openDrawer() {
        if (!this._sidebar) return;
        this._sidebar.classList.add("is-open");
        this._overlay?.classList.add("is-open");
        document.body.style.overflow = "hidden";
        this._fab?.setAttribute("aria-expanded", "true");
    },

    _closeDrawer() {
        if (!this._sidebar) return;
        this._sidebar.classList.remove("is-open");
        this._overlay?.classList.remove("is-open");
        document.body.style.overflow = "";
        this._fab?.setAttribute("aria-expanded", "false");
    },

    // ── Skeleton AJAX ─────────────────────────────────────────────────
    // Odoo dispara el evento `website_sale.filter_products` antes del XHR.
    // Aprovechamos ese momento para mostrar el estado de carga.

    _initSkeletonListener() {
        document.addEventListener("website_sale.filter_products", () => {
            this.el.classList.add("md-filtering");
        });
        document.addEventListener("website_sale.done_filter_products", () => {
            this.el.classList.remove("md-filtering");
        });
    },

    // ── Resize ────────────────────────────────────────────────────────

    _handleResize() {
        if (this._isMobile()) {
            if (!this._fab) this._setupDrawer();
        } else {
            this._teardownDrawer();
        }
    },

    // ── Utils ─────────────────────────────────────────────────────────

    _debounce(fn, delay) {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), delay);
        };
    },

    destroy() {
        window.removeEventListener("resize", this._onResize);
        this._teardownDrawer();
        return this._super(...arguments);
    },
});
