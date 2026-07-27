/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";

const STORAGE_KEY = "md_dark_mode";

function isDarkStored() {
    return localStorage.getItem(STORAGE_KEY) === "1";
}

function applyDarkClass(dark) {
    document.documentElement.classList.toggle("o_md_dark_mode", dark);
    // Tambien se fija [data-bs-theme] (convencion nativa de Bootstrap 5.3)
    // para que CSS de terceros/futuro escrito contra ese selector estandar
    // tambien funcione, sin depender solo de la clase propietaria.
    if (dark) {
        document.documentElement.setAttribute("data-bs-theme", "dark");
    } else {
        document.documentElement.removeAttribute("data-bs-theme");
    }
}

// Aplicar de inmediato al cargar el script (antes de montar OWL) para evitar
// el parpadeo de tema claro -> oscuro en cada recarga de página.
applyDarkClass(isDarkStored());

export class MdDarkModeToggle extends Component {
    static template = "md_dark_mode.SystrayIcon";
    static props = {};

    setup() {
        this.state = useState({ dark: isDarkStored() });
        onWillStart(() => applyDarkClass(this.state.dark));
    }

    toggle() {
        this.state.dark = !this.state.dark;
        localStorage.setItem(STORAGE_KEY, this.state.dark ? "1" : "0");
        applyDarkClass(this.state.dark);
    }
}

registry.category("systray").add(
    "md_dark_mode.toggle",
    { Component: MdDarkModeToggle },
    { sequence: 1 }
);
