/** @odoo-module */
/**
 * EcommerceOrdersScreen — lists pending website (e-commerce) sale orders
 * assigned to this branch's warehouse.
 *
 * Orders are fetched fresh on every mount via pos.session.get_ecommerce_orders().
 * The screen shows: Order #, Cliente, Total, Fecha, # Productos.
 *
 * Registered in "pos_pages" (Odoo 19 screen registry).
 * Rendered as a full-page overlay (storeOnOrder: false).
 *
 * Gracefully shows an empty state when website_sale is not installed.
 */

import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted } from "@odoo/owl";

export class EcommerceOrdersScreen extends Component {
    static template = "bi_pos_stock.EcommerceOrdersScreen";
    static props = {};
    static storeOnOrder = false;

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            orders: [],
            loading: false,
        });

        onMounted(() => this._loadOrders());
    }

    async _loadOrders() {
        this.state.loading = true;
        try {
            this.state.orders = await this.orm.call(
                'pos.session',
                'get_ecommerce_orders',
                [[this.pos.session.id]],
            );
        } catch (err) {
            console.error('[bi_pos_stock] Failed to load e-commerce orders:', err);
            this.notification.add(
                'No se pudieron cargar los pedidos en línea.',
                { type: 'danger', sticky: false },
            );
        } finally {
            this.state.loading = false;
        }
    }

    back() {
        this.pos.navigate('ProductScreen', { orderUuid: this.pos.selectedOrderUuid });
    }

    get orders() {
        return this.state.orders;
    }
}

registry.category("pos_pages").add("EcommerceOrdersScreen", {
    name: "EcommerceOrdersScreen",
    component: EcommerceOrdersScreen,
    route: `/pos/ui/${odoo.pos_config_id}/ecommerce-orders`,
    params: {},
});
