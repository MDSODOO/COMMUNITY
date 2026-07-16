/** @odoo-module */
/**
 * LotDetailPopup — full FEFO breakdown for a single product.
 *
 * Opened when the cashier clicks the ⓘ info button on a ProductCard.
 * Fetches all available lots for the product (branch-scoped, qty > 0) via
 * pos.session.get_product_lots_detail() and shows them in a colour-coded table.
 *
 * Columns:
 *   Posición | Lote / N° Serie | A la mano | Vencimiento | Días Restantes
 *
 * Color coding (Bootstrap):
 *   danger  — expired or ≤ 30 days
 *   warning — 31–90 days
 *   success — > 90 days
 *   secondary — no expiration date
 *
 * Props (injected by dialog service):
 *   productId   — int   — product.product ID
 *   productName — str   — display name for the header
 *   close       — Function (injected automatically by dialog service)
 */

import { Component, useState, onMounted } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import {
    getDaysLeft,
    getExpiryColorClass,
    formatExpiryDate,
} from "../../utils/lot_expiry_utils";

export class LotDetailPopup extends Component {
    static template = "bi_pos_stock.LotDetailPopup";
    static components = { Dialog };
    static props = {
        productId: Number,
        productName: { type: String, optional: true },
        close: Function,
    };

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.state = useState({ lots: [], loading: false });

        onMounted(() => this._loadLots());
    }

    async _loadLots() {
        this.state.loading = true;
        try {
            const lots = await this.orm.call(
                'pos.session',
                'get_product_lots_detail',
                [[this.pos.session.id], this.props.productId],
            );
            this.state.lots = lots;
        } catch (err) {
            console.error('[bi_pos_stock] LotDetailPopup: failed to load lots:', err);
        } finally {
            this.state.loading = false;
        }
    }

    get lots() { return this.state.lots; }
    get loading() { return this.state.loading; }
    get productName() { return this.props.productName || ''; }
    get hasExpiry() { return this.state.lots.some((l) => l.expiration_date); }

    // ── Helpers exposed to template ───────────────────────────────────────
    getDaysLeft(dateStr) { return getDaysLeft(dateStr); }
    getColorClass(dateStr) { return getExpiryColorClass(dateStr); }
    formatDate(dateStr) { return formatExpiryDate(dateStr); }
}
