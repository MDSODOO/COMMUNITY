/** @odoo-module **/
// Medicine Depot · Login Glass Island widget
// Inyecta .glass-login-island en el contenedor nativo del formulario
// de autenticación de Odoo para que el diseño Glassmorphism aplique.
// NOTA: No importar onWillStart/@odoo/owl en widgets legacy (publicWidget);
// esa importación provoca un error de compilación del bundle que impide
// la carga de todos los estilos CSS del módulo → pantalla en blanco.

import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Inyecta las clases Glassmorphism en el contenedor del login nativo.
 * Estrategia de fallback escalonada: card-body → oe_website_login_container
 * → container → parentElement, en ese orden de prioridad.
 */
function ensureGlassLoginIsland() {
    // Cubre login (.oe_login_form) y registro (.oe_signup_form): ambas
    // páginas comparten la misma isla Glassmorphism.
    const form = document.querySelector(".oe_login_form, .oe_signup_form");
    if (!form) {
        return;
    }

    const island =
        form.closest(".card-body") ||
        form.closest(".oe_website_login_container") ||
        form.closest(".container") ||
        form.parentElement;

    if (!island) {
        return;
    }

    island.classList.add("glass-login-island");

    const shell = island.closest(".card");
    if (shell) {
        shell.classList.add("glass-login-shell");
    }

    const frame = island.closest(".container");
    if (frame && frame !== island) {
        frame.classList.add("glass-login-frame");
    }

    bindSubmitSpinner(form);
}

/**
 * Item 9 · al enviar el formulario, marca el botón primario con .is-submitting
 * para mostrar el spinner CSS y evitar dobles envíos. El navegador navega tras
 * el submit, así que no hace falta limpiar el estado manualmente.
 */
function bindSubmitSpinner(form) {
    if (form.dataset.mdSpinnerBound === "1") {
        return;
    }
    form.dataset.mdSpinnerBound = "1";
    form.addEventListener("submit", () => {
        const btn = form.querySelector(".btn-primary");
        if (btn) {
            btn.classList.add("is-submitting");
            btn.setAttribute("aria-busy", "true");
        }
    });
}

// Fallback temprano: si el DOM ya está listo antes de que el widget
// arranque (posible en Odoo 19 con module preload), aplicamos la clase
// inmediatamente para evitar el flash en blanco.
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensureGlassLoginIsland, { once: true });
} else {
    ensureGlassLoginIsland();
}

publicWidget.registry.MdLoginGlassIsland = publicWidget.Widget.extend({
    selector: "body:has(.oe_login_form), body:has(.oe_signup_form)",

    start() {
        ensureGlassLoginIsland();
        return this._super(...arguments);
    },
});
