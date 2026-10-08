/** @odoo-module */
/**
 * MdKanbanLotDetailPopup — réplica del bi_pos_stock.LotDetailPopup del POS
 * (rama de lotes/FEFO), para el Kanban de Inventario > Productos. Se abre
 * desde el botón dedicado "detalle de lotes" (md_lot_detail_button widget)
 * en la card de product.template.
 *
 * A diferencia del POS (pos.session.get_product_lots_detail, acotado a la
 * sucursal/sesión activa), aquí la fuente de datos es
 * product.template.get_md_lot_detail() — agrega existencias de todas las
 * compañías activas (mismo criterio que el resto del Kanban de Inventario,
 * ver _md_onhand_lot_locations en product_template.py). Solo aplica a
 * productos con tracking lot/serial — el botón que abre este popup no se
 * renderiza para el resto (misma condición que los chips de desglose).
 */

import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { getDaysLeft, getExpiryColorClass, formatExpiryDate } from "./md_lot_expiry_utils";

export class MdKanbanLotDetailPopup extends Component {
    static template = "md_pharma_regulatory.MdKanbanLotDetailPopup";
    static components = { Dialog };
    static props = {
        productId: Number,
        productName: { type: String, optional: true },
        close: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ lots: [], loading: true });
        onWillStart(() => this._loadLots());
    }

    async _loadLots() {
        this.state.loading = true;
        try {
            this.state.lots = await this.orm.call(
                'product.template',
                'get_md_lot_detail',
                [[this.props.productId]],
            );
        } catch (err) {
            console.error('[md_pharma_regulatory] MdKanbanLotDetailPopup: failed to load lots:', err);
        } finally {
            this.state.loading = false;
        }
    }

    get lots() { return this.state.lots; }
    get loading() { return this.state.loading; }
    get productName() { return this.props.productName || ''; }
    get hasExpiry() { return this.state.lots.some((l) => l.expiration_date); }

    // ── Helpers expuestos al template (mismos nombres que LotDetailPopup del POS) ──
    getDaysLeft(dateStr) { return getDaysLeft(dateStr); }
    getColorClass(dateStr) { return getExpiryColorClass(dateStr); }
    formatDate(dateStr) { return formatExpiryDate(dateStr); }
}
