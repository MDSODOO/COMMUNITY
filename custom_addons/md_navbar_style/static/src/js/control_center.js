/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";

// Control Center: agrega en un solo panel bento lo que ya existe disperso en
// el systray (mensajes, actividades) + accesos rapidos, estilo macOS Control
// Center. No reimplementa la logica de mail.store ni del toggle de modo
// oscuro -- consume el servicio real y delega el click en los botones
// nativos ya probados (ActivityMenu, md_dark_mode toggle) en vez de
// duplicar su comportamiento.
export class ControlCenter extends Component {
    static template = "md_navbar_style.ControlCenter";
    static components = { Dropdown };
    static props = [];

    setup() {
        this.store = useService("mail.store");
        this.action = useService("action");
        this.dropdown = useDropdownState();
        this.state = useState({ dark: this.isDarkActive() });
    }

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
