/** @odoo-module **/

// Mejora 28 · Promueve alertas nativas de Odoo a píldoras flotantes.
// Observa el árbol del documento en busca de elementos .alert que
// aparezcan fuera de formularios (snippets de éxito/error post-acción)
// y los reubica dentro de #md-toast-stack con auto-dismiss + animación.
// No interfiere con alertas inline persistentes (forms con role=alert
// dentro de un wizard mantienen su sitio).

import publicWidget from "@web/legacy/js/public/public_widget";

const TOAST_LIFETIME_MS = 5200;
const PROMOTED_FLAG = "data-md-toast-promoted";

function getStack() {
    return document.getElementById("md-toast-stack");
}

function shouldPromote(alertEl) {
    if (!alertEl || alertEl.hasAttribute(PROMOTED_FLAG)) {
        return false;
    }
    if (alertEl.closest("form, .o_wizard, .md_pv_form, .md_affiliacion_form")) {
        return false;
    }
    if (alertEl.closest(".md-toast-stack")) {
        return false;
    }
    if (alertEl.classList.contains("alert-secondary")) {
        return false;
    }
    return alertEl.classList.contains("alert");
}

function promoteAlert(alertEl) {
    const stack = getStack();
    if (!stack || !shouldPromote(alertEl)) {
        return;
    }
    alertEl.setAttribute(PROMOTED_FLAG, "1");
    alertEl.classList.add("md-toast--pill");
    stack.appendChild(alertEl);

    window.setTimeout(() => {
        alertEl.style.transition = "opacity 0.25s ease, transform 0.25s ease";
        alertEl.style.opacity = "0";
        alertEl.style.transform = "translateY(-6px)";
        window.setTimeout(() => alertEl.remove(), 280);
    }, TOAST_LIFETIME_MS);
}

publicWidget.registry.MdToastPromoter = publicWidget.Widget.extend({
    selector: "body",

    start() {
        const root = this.el;
        if (!root || !getStack()) {
            return this._super(...arguments);
        }

        root.querySelectorAll(".alert:not(.md-no-toast)").forEach(promoteAlert);

        this._observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (!(node instanceof HTMLElement)) {
                        continue;
                    }
                    if (node.matches && node.matches(".alert:not(.md-no-toast)")) {
                        promoteAlert(node);
                    }
                    if (node.querySelectorAll) {
                        node.querySelectorAll(".alert:not(.md-no-toast)").forEach(promoteAlert);
                    }
                }
            }
        });
        this._observer.observe(root, { childList: true, subtree: true });

        return this._super(...arguments);
    },

    destroy() {
        if (this._observer) {
            this._observer.disconnect();
        }
        return this._super(...arguments);
    },
});
