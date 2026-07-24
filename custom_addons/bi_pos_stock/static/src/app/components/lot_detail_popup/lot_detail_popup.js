/** @odoo-module */
/**
 * LotDetailPopup — product detail popup opened from the ProductCard ⓘ button.
 *
 * Two display modes, decided by the product's tracking type:
 *
 *  1. Lot/serial-tracked products → FEFO breakdown table.
 *     Fetches all available lots (branch-scoped, qty > 0) via
 *     pos.session.get_product_lots_detail() and shows them in a
 *     colour-coded table:
 *       Posición | Lote / N° Serie | A la mano | Vencimiento | Días Restantes
 *
 *  2. Everything else → "Detalle regulatorio" fields table (no RPC needed —
 *     read directly from the already-loaded product.template record):
 *       Categoría | Referencia interna | Código de barras | Existencia
 *
 *     NOTE: the design handoff's mockup field "Línea/Marca" has no direct
 *     equivalent on product.template in stock Odoo — mapped to the POS
 *     category name instead, the closest grouping data actually available
 *     client-side without adding a new field/RPC just for this popup.
 *
 * Color coding (Bootstrap):
 *   danger  — expired or ≤ 30 days
 *   warning — 31–90 days
 *   success — > 90 days
 *   secondary — no expiration date
 *
 * Props (injected by dialog service):
 *   productId   — int   — product.template ID (see product_card.js openLotDetail)
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

        const product = this.pos.models["product.template"]?.getBy?.("id", this.props.productId);
        this.product = product || null;
        this.isLotTracked = product
            ? (product.tracking === 'lot' || product.tracking === 'serial')
            : false;

        if (this.isLotTracked) {
            onMounted(() => this._loadLots());
        }
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

    /** Regulatory detail rows for non-lot-tracked products — read from the already-loaded record, no RPC. */
    get regulatoryFields() {
        const p = this.product;
        if (!p) return [];
        const categoryName = p.pos_categ_ids?.map((c) => c.name).filter(Boolean).join(', ')
            || p.categ_id?.name
            || '—';
        const stockQty = this.pos.stockByTmplId?.[this.props.productId];
        return [
            { label: 'Categoría', value: categoryName },
            { label: 'Referencia interna', value: p.default_code || '—' },
            { label: 'Código de barras', value: p.barcode || '—' },
            { label: 'Unidad de medida', value: p.uom_id?.name || '—' },
            {
                label: 'Existencia (A la mano)',
                value: stockQty !== undefined ? `${stockQty} pzas en esta sucursal` : '—',
            },
        ];
    }

    // ── Helpers exposed to template ───────────────────────────────────────
    getDaysLeft(dateStr) { return getDaysLeft(dateStr); }
    getColorClass(dateStr) { return getExpiryColorClass(dateStr); }
    formatDate(dateStr) { return formatExpiryDate(dateStr); }
}
