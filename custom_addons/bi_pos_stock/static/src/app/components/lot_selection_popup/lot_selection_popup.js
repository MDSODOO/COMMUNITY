/** @odoo-module */
/**
 * LotSelectionPopup — FEFO lot picker opened when the cashier taps a
 * lot/serial-tracked ProductCard.
 *
 * Replaces Odoo's native SelectLotPopup (manual lot-number text entry, one
 * field per unit) for products where we already have cached FEFO lot data
 * (pos.allLotDetails, loaded once at session open). Instead, the cashier sees
 * every lot at once with a quantity stepper per row — the earliest-expiry
 * (FEFO) lot preselected at qty 1 — and can split the requested quantity
 * across several lots in one confirmation.
 *
 * Falls back to the native flow (see product_list.js) when no cached lot data
 * exists for the product — e.g. product_expiry not installed, or genuinely
 * zero on-hand stock — so this popup never shows an unusable empty table.
 *
 * Writes directly on the native pos.order / pos.order.line structures via
 * PosStore.addLineToOrder() + PosOrderline.setPackLotLines() (through the
 * shared assignLotToLine() helper) — no parallel cart/lot data model.
 */

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import {
    getDaysLeft,
    getExpiryColorClass,
    formatExpiryDate,
    formatQty,
} from "../../utils/lot_expiry_utils";
import { getFefoLotsForTemplate, assignLotToLine } from "../../utils/lot_stock_utils";
import { _t } from "@web/core/l10n/translation";

export class LotSelectionPopup extends Component {
    static template = "bi_pos_stock.LotSelectionPopup";
    static components = { Dialog };
    static props = {
        productName: { type: String, optional: true },
        variantIds: Array,
        close: Function,
    };

    setup() {
        this.pos = usePos();
        // Snapshot once at open time — the cashier works off a stable list for
        // the duration of the popup, same as the design prototype (no live
        // refetch while steppers are being adjusted).
        this.lots = getFefoLotsForTemplate(this.pos, this.props.variantIds);

        const initialQty = {};
        if (this.lots.length) {
            // FEFO lot (index 0) preselected at qty 1, per interaction spec.
            initialQty[this.lots[0].key] = 1;
        }
        this.state = useState({ qtyByLot: initialQty });
    }

    get productName() {
        return this.props.productName || '';
    }

    get hasLots() {
        return this.lots.length > 0;
    }

    // Keyed by lot.key ("{variantId}_{lot_name}"), not lot_name alone — see
    // getFefoLotsForTemplate() in lot_stock_utils.js for why.
    lotQty(lotKey) {
        return this.state.qtyByLot[lotKey] || 0;
    }

    setLotQty(lotKey, value) {
        // "A la mano" (On Hand) hard cap - sin esto, inc() dejaba subir la
        // cantidad de un lote por encima de lo que declara la propia fila
        // ("de N pzas"), permitiendo agregar al ticket mas de lo que existe
        // fisicamente para ese lote. Espejo del mismo tope que ya aplica
        // lot_cascade_patch.js en las rutas de numpad/+-.
        const lot = this.lots.find((l) => l.key === lotKey);
        const max = lot ? lot.qty : Infinity;
        const clamped = Math.min(Math.max(0, value), max);
        if (value > max) {
            this.env.services.notification?.add(
                _t('Solo hay %(max)s "A la mano" para el lote %(lot)s.', { max, lot: lot?.lot_name }),
                { type: "warning" }
            );
        }
        this.state.qtyByLot[lotKey] = clamped;
    }

    inc(lotKey) {
        this.setLotQty(lotKey, this.lotQty(lotKey) + 1);
    }

    dec(lotKey) {
        this.setLotQty(lotKey, this.lotQty(lotKey) - 1);
    }

    /** Row click toggles between 0 and 1 — same convenience as the design prototype. */
    toggleRow(lotKey) {
        this.setLotQty(lotKey, this.lotQty(lotKey) > 0 ? 0 : 1);
    }

    get totalQty() {
        return Object.values(this.state.qtyByLot).reduce((s, q) => s + (q || 0), 0);
    }

    get hasSelection() {
        return this.totalQty > 0;
    }

    get confirmLabel() {
        const total = this.totalQty;
        if (total <= 0) return 'Sin selección';
        return `Agregar al ticket — ${formatQty(total)} pza${total === 1 ? '' : 's'}`;
    }

    // ── Row helpers exposed to the template ─────────────────────────────────
    isFefo(index) {
        return index === 0;
    }

    daysLeft(dateStr) {
        return getDaysLeft(dateStr);
    }

    colorClass(dateStr) {
        return getExpiryColorClass(dateStr);
    }

    dateLabel(dateStr) {
        return formatExpiryDate(dateStr);
    }

    /**
     * Confirms the selection: adds one order line per lot with qty > 0.
     *
     * Uses addLineToOrder(configure=false) — same pattern as the automatic
     * FEFO cascade (lot_cascade_patch.js) — so neither this popup nor the
     * cascade ever triggers the native SelectLotPopup on top of each other.
     */
    async confirm() {
        if (!this.hasSelection) return;

        const order = this.pos.getOrder();
        for (const lot of this.lots) {
            const qty = this.lotQty(lot.key);
            if (qty <= 0) continue;

            const variant = this.pos.models["product.product"].getBy("id", lot.productId);
            if (!variant) continue;

            const newLine = await this.pos.addLineToOrder(
                { product_id: variant, product_tmpl_id: variant.product_tmpl_id },
                order,
                false,
                {}
            );
            if (newLine) {
                assignLotToLine(newLine, lot.lot_name);
                newLine.setQuantity(qty);
            }
        }
        this.props.close();
    }
}
