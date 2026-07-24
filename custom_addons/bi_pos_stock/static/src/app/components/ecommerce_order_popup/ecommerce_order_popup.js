/** @odoo-module */
/**
 * EcommerceOrderPopup — shown when a new website order is confirmed
 * and the POS receives an ECOMMERCE_ORDER bus message.
 *
 * Opened via the dialog service: this.dialog.add(EcommerceOrderPopup, { ...props }).
 * The dialog service injects `close` automatically.
 *
 * Props:
 *   orderName      — str  e.g. "S00042"
 *   partnerName    — str  customer name
 *   amountTotal    — float
 *   currencySymbol — str  e.g. "$"
 *   productCount   — int
 *   close          — Function  (injected by dialog service)
 *
 * The "Ver Pedidos" button navigates to EcommerceOrdersScreen via usePos().
 */

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class EcommerceOrderPopup extends Component {
    static template = "bi_pos_stock.EcommerceOrderPopup";
    static components = { Dialog };
    static props = {
        orderName: String,
        partnerName: String,
        amountTotal: Number,
        currencySymbol: { type: String, optional: true },
        productCount: Number,
        close: Function,
    };

    setup() {
        this.pos = usePos();
    }

    get currencySymbol() {
        return this.props.currencySymbol || "$";
    }

    viewOrders() {
        this.props.close();
        this.pos.navigate("EcommerceOrdersScreen");
    }
}
