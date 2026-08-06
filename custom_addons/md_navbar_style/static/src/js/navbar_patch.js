/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.mdsState = useState({
            customFeaturesReady: true,
        });
    },

    // Punto de extensión para futuras integraciones en la zona custom del navbar
    onMdsCustomActionClick(actionId) {
        if (this.env.services.action) {
            this.env.services.action.doAction(actionId);
        }
    }
});
