/** @odoo-module */
/**
 * POS theme mode patch.
 *
 * Odoo 19 POS follows OS prefers-color-scheme for dark mode. If the POS
 * config explicitly requests light mode (iface_theme = 'light'), this patch
 * adds body.pos-force-light so that our @media dark-mode CSS is suppressed.
 *
 * Graceful no-op when iface_theme field doesn't exist in this Odoo version.
 */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData(...arguments);

        const theme = this.config?.iface_theme;
        if (theme === "light") {
            document.body.classList.add("pos-force-light");
        } else {
            document.body.classList.remove("pos-force-light");
        }
    },
});
