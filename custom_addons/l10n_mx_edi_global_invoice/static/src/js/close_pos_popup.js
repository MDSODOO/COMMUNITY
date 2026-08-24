/** @odoo-module */
import {ClosePosPopup} from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import {patch} from "@web/core/utils/patch";
import {_t} from "@web/core/l10n/translation";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";


patch(ClosePosPopup.prototype, {
    //@override
    async confirm() {
        //GET RELATIONED ORDERS WITOUTH INVOICE
        const len_orders = await  this.pos.data.call('pos.session', "get_orders_uninvoiced", [this.pos.session.id])
        let do_factura_global = false
        if (len_orders > 0) {
            const response = await ask(this.dialog, {
                title: _t('Facturación global'),
                body: _t('Hay ' + len_orders + " órdenes sin facturar, ¿Desea generar una factura global para todas las órdenes no facturadas?"),
            });
            do_factura_global = response
             await this.pos.data.call('pos.session', "set_option_global_inv_active", [this.pos.session.id,do_factura_global])
        }

        return super.confirm();

    },

});
