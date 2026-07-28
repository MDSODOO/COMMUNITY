/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";

// ════════════════════════════════════════════════════════════════════════
// MdLauncher — fusión de md_command_palette + md_home_menu en un solo
// componente con un único estado `open`, activable tanto por teclado
// (Ctrl+K / Alt+Espacio) como por click en el botón de Apps de la NavBar
// nativa (".o_navbar_apps_menu").
//
// Se sigue montando una sola vez como main_component del WebClient (mismo
// mecanismo que DialogContainer/NotificationContainer nativos de Odoo) en
// vez de parchear NavBar.js — evita fragilidad ante updates del core.
//
// Por qué interceptar el click del botón de Apps con un listener en fase
// de captura (en vez de heredar/reemplazar el <Dropdown> nativo vía XML,
// que es lo que hacía md_home_menu): el <Dropdown> de
// web.NavBar.AppsMenu adjunta su propio toggle sobre el <button> nativo
// (ver navbar.xml del core, t-name="web.NavBar.AppsMenu") y ese mecanismo
// interno no expone un hook público para "abrir esto otro en su lugar".
// La misma técnica que ya usa este módulo para ganarle al hotkey service
// nativo en Ctrl+K (listener en window, fase de captura, stopPropagation)
// funciona igual aquí: nuestro listener se ejecuta ANTES de que el evento
// llegue al <button> del Dropdown, así que su propio handler de toggle
// nunca se dispara. El <Dropdown> nativo sigue existiendo en el DOM sin
// tocarlo — solo evitamos que reciba el click.
// Contrato de "acciones rapidas": cualquier modulo puede empujar entradas a
// registry.category("md_launcher_quick_actions") sin que este modulo (ni el
// que las registra) se declaren dependencia mutua -- mismo desacoplamiento
// que ya usan los registries nativos de Odoo (systray, main_components).
// Cada entrada: { id, label, keywords?: string[], icon?: string (clase fa-*),
// run(env) }. "run" recibe el Env de OWL (con .services) para que quien
// registra decida que hacer (abrir un Dialog, navegar, etc.) sin que
// MdLauncher necesite conocer detalles de negocio.
//
// Se agrego tras la auditoria del 2026-07-28: el "Copiloto de inventario"
// (commit 80e3573, 2026-07-27) se registro con useCommand() asumiendo que
// alimentaria el Command Palette NATIVO de Odoo -- pero este modulo
// intercepta Ctrl+K/Alt+Espacio en fase de captura con
// stopImmediatePropagation() (ver _onGlobalKeydown) antes de que el hotkey
// service nativo (del que depende useCommand) lo reciba. Confirmado en vivo:
// buscar "copiloto" o "inventario" en esta paleta no devolvia nada. Este
// registry es el arreglo de raiz -- ver local_ai_connector/static/src/js/
// launcher_quick_actions.js.
const QUICK_ACTIONS_CATEGORY = "md_launcher_quick_actions";

export class MdLauncher extends Component {
    static template = "md_command_palette.Launcher";
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
            quickActionResults: [],
            suggestedApps: [],
            activeIndex: 0,
        });

        this.inputRef = useRef("paletteInput");
        this._searchProducts = debounce(this._searchProducts.bind(this), 250);

        // Elemento al que se restituye el foco de teclado al cerrar
        // (botón de Apps si se abrió por click, o el elemento que tenía
        // foco al momento de disparar Ctrl+K/Alt+Espacio). Bug de
        // accesibilidad detectado en la auditoría: close() no restituía
        // el foco, dejando al usuario de teclado "perdido" en <body>.
        this._triggerEl = null;
        this._appsButtonEl = null;

        this._onGlobalKeydown = this._onGlobalKeydown.bind(this);
        this._onGlobalClickCapture = this._onGlobalClickCapture.bind(this);
        // Fase de captura: intercepta Ctrl+K / Alt+Space antes que el
        // hotkey service nativo de Odoo y antes que el navegador; e
        // intercepta el click del botón de Apps antes que el <Dropdown>
        // nativo de web.NavBar.AppsMenu.
        onMounted(() => {
            window.addEventListener("keydown", this._onGlobalKeydown, true);
            window.addEventListener("click", this._onGlobalClickCapture, true);
            // Sincroniza la semántica ARIA del botón nativo: sigue
            // anunciándose como si abriera el <Dropdown> de Odoo (que
            // nunca se abre en la práctica, ver comentario de
            // _onGlobalClickCapture) cuando en realidad abre este modal.
            // aria-expanded se actualiza en open()/close().
            this._appsButtonEl = document.querySelector(".o_navbar_apps_menu");
            this._appsButtonEl?.setAttribute("aria-haspopup", "dialog");
        });
        onWillUnmount(() => {
            window.removeEventListener("keydown", this._onGlobalKeydown, true);
            window.removeEventListener("click", this._onGlobalClickCapture, true);
        });
    }

    _isShortcut(ev) {
        const ctrlK = (ev.ctrlKey || ev.metaKey) && !ev.shiftKey && !ev.altKey && ev.key.toLowerCase() === "k";
        const altSpace = ev.altKey && !ev.ctrlKey && !ev.shiftKey && ev.code === "Space";
        return ctrlK || altSpace;
    }

    _onGlobalKeydown(ev) {
        if (this._isShortcut(ev)) {
            ev.preventDefault();
            // stopImmediatePropagation (no solo stopPropagation): defensa
            // en profundidad. Odoo core registra su propia Command Palette
            // nativa en "control+k" (command_service.js, vía hotkeyService,
            // fase burbuja) — el análisis de fases de eventos indica que
            // capturar en `window` con stopPropagation ya alcanza para
            // ganarle la carrera, pero si algún día el core cambia a fase
            // de captura, stopPropagation() no bastaría para suprimir
            // otros listeners registrados en el MISMO target (window).
            // stopImmediatePropagation() sí lo garantiza. Ver auditoría:
            // riesgo de doble modal (paleta nativa + MdLauncher) nunca
            // observado en vivo, pero prevenible sin costo.
            ev.stopImmediatePropagation();
            if (!this.state.open) {
                // Se abre por teclado: recordar qué tenía el foco para
                // restituirlo al cerrar (no hay botón de Apps involucrado).
                this._triggerEl = document.activeElement;
            }
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

    // Botón de Apps de la NavBar nativa (".o_navbar_apps_menu button" en
    // desktop). En mobile (ui.isSmall) Odoo renderiza en su lugar
    // ".o_menu_toggle" (sidebar deslizable) — fuera de alcance de esta
    // unificación a propósito: ese patrón de burger-menu es un paradigma
    // de navegación distinto (drawer full-height) y no compite con el
    // spotlight; se deja intacto.
    _onGlobalClickCapture(ev) {
        const appsButton = ev.target.closest(".o_navbar_apps_menu");
        if (!appsButton) return;
        ev.preventDefault();
        ev.stopPropagation();
        // Se abre por click en el botón de Apps: ese botón es el que
        // recupera el foco al cerrar.
        this._triggerEl = appsButton;
        this.toggle();
    }

    get results() {
        // Paleta vacía (sin búsqueda activa): "Acciones Sugeridas" =
        // mismo listado de apps instaladas que usaba el grid de
        // md_home_menu (menuService.getApps()), ahora dentro de este
        // componente en vez de en el <Dropdown> nativo.
        if (!this.state.query.trim()) {
            return this.state.suggestedApps.map((app) => ({
                type: "app",
                key: `app-${app.id}`,
                label: app.name,
                iconUrl: app.webIconData || null,
                app,
            }));
        }
        return [...this.state.quickActionResults, ...this.state.menuResults, ...this.state.productResults];
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
        this.state.menuResults = [];
        this.state.productResults = [];
        // Mismo dataset que consumía md_home_menu para pintar su grid de
        // iconos — reutilizado tal cual, sin duplicar la fuente de datos.
        this.state.suggestedApps = this.menuService.getApps();
        this._appsButtonEl?.setAttribute("aria-expanded", "true");
        requestAnimationFrame(() => this.inputRef.el?.focus());
    }

    close() {
        this.state.open = false;
        this._appsButtonEl?.setAttribute("aria-expanded", "false");
        // Restituye el foco de teclado al disparador (botón de Apps o
        // elemento que tenía foco antes de Ctrl+K). Bug de accesibilidad
        // detectado en la auditoría: sin esto, el foco caía a <body> tras
        // cerrar con Escape o al seleccionar un resultado.
        this._triggerEl?.focus?.();
        this._triggerEl = null;
    }

    onInput(ev) {
        const query = ev.target.value;
        this.state.query = query;
        this.state.activeIndex = 0;
        if (!query.trim()) {
            // Volver al estado "Acciones Sugeridas" en vez de repetir la
            // búsqueda de menús con query vacía (ese era el bug detectado
            // en la auditoría: _searchMenus("") devolvía los primeros 6
            // resultados de menuService.getAll() en el orden interno del
            // árbol de menús — en la práctica, submenús de "Ajustes" sin
            // ninguna relación con "sugerencias útiles").
            this.state.menuResults = [];
            this.state.productResults = [];
            this.state.quickActionResults = [];
            return;
        }
        this._searchQuickActions(query);
        this._searchMenus(query);
        this._searchProducts(query);
    }

    _searchQuickActions(query) {
        const q = query.trim().toLowerCase();
        const all = registry.category(QUICK_ACTIONS_CATEGORY).getAll();
        this.state.quickActionResults = all
            .filter((action) => {
                const haystack = [action.label, ...(action.keywords || [])].join(" ").toLowerCase();
                return haystack.includes(q);
            })
            .map((action) => ({
                type: "quickaction",
                key: `quickaction-${action.id}`,
                label: action.label,
                icon: action.icon || "fa-bolt",
                action,
            }));
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
        if (item.type === "menu" || item.type === "app") {
            this.menuService.selectMenu(item.type === "app" ? item.app : item.menu);
        } else if (item.type === "quickaction") {
            item.action.run(this.env);
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

registry.category("main_components").add("md_command_palette.Launcher", {
    Component: MdLauncher,
});
