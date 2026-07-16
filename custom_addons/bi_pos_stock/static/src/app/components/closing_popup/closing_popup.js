/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ClosePosPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
    },

    async downloadCloseCashReport() {
        const sessionId = this.pos.session?.id;
        if (!sessionId) {
            return;
        }
        const action = await this.pos.data.call(
            "pos.session",
            "action_print_cierre_caja_report",
            [[sessionId]]
        );
        if (action) {
            await this.actionService.doAction(action);
        }
    },
});
