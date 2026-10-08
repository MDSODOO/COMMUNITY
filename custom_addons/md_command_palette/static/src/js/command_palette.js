/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";

// Se monta una sola vez como main_component del WebClient (mismo mecanismo
// que usan DialogContainer / NotificationContainer nativos de Odoo), en vez
// de parchear NavBar.js directamente — evita fragilidad ante updates del core.
export class MdCommandPalette extends Component {
    static template = "md_command_palette.CommandPalette";
    static props = {};

    setup() {
        this.menuService = useService("menu");
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            open: false,
            query: "",
            menuResults: [],
            productResults: [],
            activeIndex: 0,
        });

        this.inputRef = useRef("paletteInput");
        this._searchProducts = debounce(this._searchProducts.bind(this), 250);

        this._onGlobalKeydown = this._onGlobalKeydown.bind(this);
        // Fase de captura: intercepta Ctrl+K / Alt+Space antes que el
        // hotkey service nativo de Odoo y antes que el navegador.
        onMounted(() => window.addEventListener("keydown", this._onGlobalKeydown, true));
        onWillUnmount(() => window.removeEventListener("keydown", this._onGlobalKeydown, true));
    }

    _isShortcut(ev) {
        const ctrlK = (ev.ctrlKey || ev.metaKey) && !ev.shiftKey && !ev.altKey && ev.key.toLowerCase() === "k";
        const altSpace = ev.altKey && !ev.ctrlKey && !ev.shiftKey && ev.code === "Space";
        return ctrlK || altSpace;
    }

    _onGlobalKeydown(ev) {
        if (this._isShortcut(ev)) {
            ev.preventDefault();
            ev.stopPropagation();
            this.toggle();
            return;
        }
        if (!this.state.open) return;

        if (ev.key === "Escape") {
            ev.preventDefault();
            this.close();
        } else if (ev.key === "ArrowDown") {
            ev.preventDefault();
            this._moveActive(1);
        } else if (ev.key === "ArrowUp") {
            ev.preventDefault();
            this._moveActive(-1);
        } else if (ev.key === "Enter") {
            ev.preventDefault();
            this._selectActive();
        }
    }

    get results() {
        return [...this.state.menuResults, ...this.state.productResults];
    }

    _moveActive(delta) {
        const total = this.results.length;
        if (!total) return;
        this.state.activeIndex = (this.state.activeIndex + delta + total) % total;
    }

    _selectActive() {
        const item = this.results[this.state.activeIndex];
        if (item) this._activate(item);
    }

    toggle() {
        this.state.open ? this.close() : this.open();
    }

    open() {
        this.state.open = true;
        this.state.query = "";
        this.state.activeIndex = 0;
        this._searchMenus("");
        this.state.productResults = [];
        requestAnimationFrame(() => this.inputRef.el?.focus());
    }

    close() {
        this.state.open = false;
    }

    onInput(ev) {
        const query = ev.target.value;
        this.state.query = query;
        this.state.activeIndex = 0;
        this._searchMenus(query);
        this._searchProducts(query);
    }

    _searchMenus(query) {
        const all = this.menuService.getAll();
        // Solo el menú raíz de cada app trae webIconData — los submenús
        // (m.id !== m.appID) heredan visualmente el ícono de su app.
        const appsById = new Map(all.filter((m) => m.id === m.appID).map((m) => [m.id, m]));
        const candidates = all.filter((m) => m.actionID && m.id !== "root");
        const q = query.trim().toLowerCase();
        const filtered = (q ? candidates.filter((m) => m.name.toLowerCase().includes(q)) : candidates).slice(0, 6);
        this.state.menuResults = filtered.map((m) => {
            const app = appsById.get(m.appID);
            return {
                type: "menu",
                key: `menu-${m.id}`,
                label: m.name,
                // webIconData ya es un data-URI completo ("data:image/png;base64,...."),
                // no base64 crudo — verificado en vivo (menu_service.js, Odoo 19).
                iconUrl: (app && app.webIconData) || null,
                menu: m,
            };
        });
    }

    // La cookie `cids` (ej. "7" o "7-2-3") es la misma fuente que usa el
    // propio cliente de Odoo para fijar allowed_company_ids en cada request;
    // el primer id es la compañía/sucursal activa en el selector del navbar.
    // Verificado en vivo: qty_available SIN este override suma las 6
    // sucursales (269 uds.) en vez de solo la activa (5 uds. en Mérida).
    _getActiveCompanyId() {
        const match = document.cookie.match(/(?:^|;\s*)cids=([^;]+)/);
        if (!match) return null;
        const id = parseInt(match[1].split(/[-,]/)[0], 10);
        return Number.isNaN(id) ? null : id;
    }

    async _searchProducts(query) {
        const q = query.trim();
        if (q.length < 2) {
            this.state.productResults = [];
            return;
        }
        const companyId = this._getActiveCompanyId();
        const records = await this.orm.searchRead(
            "product.product",
            [["name", "ilike", q], ["qty_available", ">", 0]],
            ["display_name", "qty_available", "uom_id", "product_tmpl_id"],
            {
                limit: 5,
                context: companyId ? { allowed_company_ids: [companyId] } : {},
            }
        );
        // Regla inquebrantable: SIEMPRE "A la mano" — nunca "Disponible"/"Stock".
        this.state.productResults = records.map((r) => ({
            type: "product",
            key: `product-${r.id}`,
            label: r.display_name,
            onHand: r.qty_available,
            uom: r.uom_id ? r.uom_id[1] : "",
            imageUrl: `/web/image/product.product/${r.id}/image_128`,
            record: r,
        }));
    }

    _activate(item) {
        this.close();
        if (item.type === "menu") {
            this.menuService.selectMenu(item.menu);
        } else if (item.type === "product") {
            // Abre product.template (no product.product): es el modelo que
            // usa el menú "Productos" normal — product.product tiene su
            // propio set de vistas de formulario (más simple, para
            // variantes) y se veía distinto a lo que el usuario espera.
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "product.template",
                res_id: item.record.product_tmpl_id[0],
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    onItemClick(item) {
        this._activate(item);
    }
}

registry.category("main_components").add("md_command_palette.CommandPalette", {
    Component: MdCommandPalette,
});
