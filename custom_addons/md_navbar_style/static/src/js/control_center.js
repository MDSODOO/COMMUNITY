/** @odoo-module **/

import { Component, useState, onMounted, onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";

// Control Center: agrega en un solo panel bento lo que ya existe disperso en
// el systray (mensajes, actividades, copiloto IA, precios, empresa, modo
// oscuro) + Ajustes, estilo macOS Control Center. No reimplementa la logica
// de ningun modulo -- consume mail.store donde aplica y delega el click en
// los botones/componentes nativos ya probados (ActivityMenu, md_dark_mode
// toggle, local_ai_connector, purchase_invoice_parser, selector de
// compania nativo) en vez de duplicar su comportamiento.
export class ControlCenter extends Component {
    static template = "md_navbar_style.ControlCenter";
    static components = { Dropdown };
    static props = [];

    setup() {
        this.store = useService("mail.store");
        this.action = useService("action");
        this.dropdown = useDropdownState();
        this.state = useState({ dark: this.isDarkActive() });

        // Bug PREEXISTENTE de purchase_invoice_parser (confirmado en vivo
        // 2026-08-06, incluso con click DIRECTO en el trigger nativo, sin
        // pasar por este componente): PriceNotificationMenu implementa su
        // cierre-al-click-afuera con this.__owl__.bdom?.el, una API interna
        // de OWL no publica -- no resuelve en esta version y el dropdown
        // nunca se cierra solo. No se edita el archivo original del modulo;
        // se corrige desde aqui reabriendo (=cerrando, toggle()) el mismo
        // trigger nativo cuando se detecta un click fuera de
        // .pip_price_notification mientras esta abierto, mismo patron de
        // delegacion que el resto de este componente.
        onMounted(() => {
            document.addEventListener("click", this._closePipOnOutsideClick, true);
        });
        onWillDestroy(() => {
            document.removeEventListener("click", this._closePipOnOutsideClick, true);
        });
    }

    _closePipOnOutsideClick = (ev) => {
        const dropdown = document.querySelector(".pip_dropdown.show");
        if (!dropdown) return;
        const container = document.querySelector(".pip_price_notification");
        if (container && !container.contains(ev.target)) {
            document.querySelector(".pip_price_notification .o_nav_entry")?.click();
        }
    };

    isDarkActive() {
        return document.documentElement.classList.contains("o_md_dark_mode");
    }

    onBeforeOpen() {
        this.state.dark = this.isDarkActive();
    }

    openMessages() {
        this.dropdown.close();
        this.action.doAction({ tag: "mail.action_discuss", type: "ir.actions.client" });
    }

    openActivities() {
        // Delega en el boton nativo de ActivityMenu (mail) en vez de
        // adivinar una action window -- evita reimplementar su logica de
        // agrupacion por modelo.
        this.dropdown.close();
        const icon = document.querySelector(".o_menu_systray i.fa-clock-o");
        icon?.closest("button")?.click();
    }

    openSettings() {
        this.dropdown.close();
        this.action.doAction("base_setup.action_general_configuration");
    }

    openCopilot() {
        // Delega en local_ai_connector (systray "Copiloto de inventario",
        // t-on-click="openDialog") -- abre su propio Dialog, no reimplementa
        // el flujo de pregunta/respuesta aqui.
        this.dropdown.close();
        document.querySelector(".o_ai_inventory_query_toggle")?.click();
    }

    openPriceUpdates() {
        // Delega en purchase_invoice_parser (systray "Actualizaciones de
        // precio de proveedores", .pip_price_notification).
        this.dropdown.close();
        document.querySelector(".pip_price_notification .o_nav_entry")?.click();
    }

    openCompanySwitcher() {
        // Delega en el selector nativo de compania de Odoo
        // (.o_switch_company_menu) -- no reimplementa la logica de
        // multi-compania.
        this.dropdown.close();
        document.querySelector(".o_switch_company_menu button")?.click();
    }

    // El icono nativo de debug (.o_debug_manager, fa-bug) no esta solo
    // oculto por CSS: web/static/src/webclient/webclient.js SOLO lo
    // registra en el systray "if (this.env.debug)" -- si el modo
    // desarrollador esta apagado, el componente ni siquiera se monta. Se
    // replica exactamente esa misma condicion aqui (mismo this.env.debug,
    // Component de OWL) para que el tile aparezca/desaparezca en sincronia
    // con el icono nativo, no sea un tile fantasma cuando debug esta OFF.
    get isDebugMode() {
        return Boolean(this.env.debug);
    }

    openDebugMenu() {
        this.dropdown.close();
        document.querySelector(".o_debug_manager button")?.click();
    }

    toggleDarkMode() {
        // Delega en el toggle real de md_dark_mode (localStorage + clase +
        // atributo data-bs-theme) en vez de duplicar esa logica aqui.
        const toggle = document.querySelector(".o_md_dark_mode_toggle");
        toggle?.click();
        this.state.dark = this.isDarkActive();
    }
}

registry.category("systray").add(
    "md_navbar_style.control_center",
    { Component: ControlCenter },
    { sequence: 0 }
);
