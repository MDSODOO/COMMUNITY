/** @odoo-module */
/**
 * ReplenishmentLine — one row in the StockScreen tables.
 *
 * Renders differently based on props.lineType:
 *   - 'inventory': Producto | Cód. Proveedor | A la Mano | Mes1 | Mes2 | Mes3 | Acción
 *   - 'restock':   Producto | A la mano | Mín | Máx | Por ordenar | Acción
 *
 * Props:
 *   product     — plain dict from backend RPC
 *   lineType    — 'inventory' | 'restock'
 *   requesting  — bool, true while the parent RPC is in flight for this row
 *   onSolicitar — callback() called when "Solicitar" button is clicked
 */

import { Component } from "@odoo/owl";

export class ReplenishmentLine extends Component {
    static template = "bi_pos_stock.ReplenishmentLine";
    static props = {
        product:    { type: Object },
        lineType:   { type: String },
        bfLabel:    { type: [String, Boolean], optional: true },
        requesting: { type: Boolean, optional: true },
        onSolicitar:{ type: Function },
    };

    formatQty(value) {
        return Number(value || 0).toFixed(0);
    }
}
