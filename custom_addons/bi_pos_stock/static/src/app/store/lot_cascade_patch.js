/** @odoo-module */
/**
 * Lot cascade patch — auto-split lines when qty exceeds a lot's available stock.
 *
 * Problem solved:
 *   The cashier assigns Lot A (stock: 3) to a product and types qty = 7.
 *   Without this patch the line either gets blocked or silently exceeds the lot.
 *   With this patch:
 *     - Line 1 → Product X · Lot A · qty 3  (capped at Lot A's stock)
 *     - Line 2 → Product X · Lot B · qty 4  (next FEFO lot, auto-assigned)
 *   The cashier never has to think about which lot comes next.
 *
 * Data source:
 *   pos.allLotDetails  — pre-loaded at session open by get_all_lot_details().
 *   Key format: "{product.product.id}_{lot_name}"  → { product_id, qty, expiration_date }
 *
 * Intercepted paths:
 *   A) Numpad typing   → OrderSummary._setValue(bufferValue)
 *   B) +/- buttons     → OrderSummary.updateQuantityNumber(newQty)
 *
 * getLotStock/getFefoLots/assignLotToLine now live in utils/lot_stock_utils.js
 * so LotSelectionPopup (the manual "click card, pick lots" flow) shares the
 * exact same data reading + line-assignment primitive as this automatic
 * overflow cascade — no parallel FEFO implementation to keep in sync.
 */

import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { getLotStock, getFefoLots, assignLotToLine } from "../utils/lot_stock_utils";

// ── Pure data helpers ─────────────────────────────────────────────────────────

/**
 * Return the lot_name of the first pack_lot on a line, or null if none.
 */
function getLineLot(line) {
    return line.pack_lot_ids?.[0]?.lot_name || null;
}

// ── Core cascade logic ────────────────────────────────────────────────────────

/**
 * Check whether cascade should trigger and, if so, execute it.
 *
 * Caps `sourceLine` to its lot's available stock, then creates new order lines
 * for the overflow — each assigned to the next available FEFO lot.
 *
 * @param {Object}  pos          PosStore instance
 * @param {Object}  order        Current PosOrder
 * @param {Object}  sourceLine   The PosOrderline being edited
 * @param {number}  requestedQty The qty the cashier requested on that line
 * @returns {{ triggered: boolean, addedInfo: string[], missing: number }}
 */
async function cascadeLotFill(pos, order, sourceLine, requestedQty) {
    const product = sourceLine.product_id;

    // Only for lot/serial tracked products with stock data loaded
    if (!product?.tracking || product.tracking === 'none') {
        return { triggered: false, addedInfo: [], missing: 0 };
    }
    if (!pos.allLotDetails || !pos.config.pos_display_stock) {
        return { triggered: false, addedInfo: [], missing: 0 };
    }

    const currentLotName = getLineLot(sourceLine);
    if (!currentLotName) {
        return { triggered: false, addedInfo: [], missing: 0 };
    }

    const lotStock = getLotStock(pos, product.id, currentLotName);

    // Nothing to do when the requested qty fits within this lot
    if (requestedQty <= lotStock) {
        return { triggered: false, addedInfo: [], missing: 0 };
    }

    // ── Cap the current line to the lot's available stock ─────────────────────
    sourceLine.setQuantity(lotStock);

    // ── Walk FEFO lots starting from the one AFTER the current ───────────────
    const fefoLots = getFefoLots(pos, product.id);
    const currentIdx = fefoLots.findIndex(l => l.lot_name === currentLotName);
    const nextLots = currentIdx >= 0 ? fefoLots.slice(currentIdx + 1) : fefoLots;

    let remaining = requestedQty - lotStock;
    const addedInfo = [];

    for (const lotDetail of nextLots) {
        if (remaining <= 0) break;

        const qtyForLot = Math.min(remaining, lotDetail.qty);

        // Add line with configure=false to skip the lot-selection popup.
        // The stock block check in addLineToOrder sees qty=1 at this point —
        // fine, since the lot stock is valid. We set the real qty right after.
        const newLine = await pos.addLineToOrder(
            { product_id: product, product_tmpl_id: product.product_tmpl_id },
            order,
            false,  // configure — must reach base; skip popup
            {}
        );

        if (newLine) {
            assignLotToLine(newLine, lotDetail.lot_name);
            newLine.setQuantity(qtyForLot);
            addedInfo.push(`${lotDetail.lot_name} × ${qtyForLot}`);
            remaining -= qtyForLot;
        }
    }

    return { triggered: true, addedInfo, missing: remaining };
}

// ── OrderSummary patch ────────────────────────────────────────────────────────

patch(OrderSummary.prototype, {

    // ── Path A: Numpad ────────────────────────────────────────────────────────
    /**
     * Called on every keypress in the numpad when mode = "quantity".
     * We detect an over-lot-stock value, cap the line synchronously,
     * reset the buffer so subsequent keystrokes start fresh, and kick
     * off an async cascade for the overflow qty.
     */
    _setValue(val) {
        if (val !== "remove" && this.pos.numpadMode === "quantity") {
            const newQty = parseFloat(val);

            if (!isNaN(newQty) && newQty > 0) {
                let line = this.currentOrder?.getSelectedOrderline();
                if (line?.combo_parent_id) line = line.combo_parent_id;

                if (line) {
                    const lotName = getLineLot(line);
                    const product = line.product_id;

                    if (lotName && product?.tracking && product.tracking !== 'none') {
                        const lotStock = getLotStock(this.pos, product.id, lotName);

                        if (lotStock > 0 && newQty > lotStock) {
                            // 1. Set current line to lot stock (synchronous)
                            super._setValue(String(lotStock));
                            // 2. Clear the buffer so the next digit goes to a fresh value
                            this.numberBuffer.reset();
                            // 3. Cascade overflow to next lots (async, non-blocking)
                            const overflow = newQty - lotStock;
                            this._cascadeToNextLots(line, overflow);
                            return; // skip the default super._setValue(val)
                        }
                    }
                }
            }
        }
        return super._setValue(val);
    },

    // ── Path B: +/− quantity buttons ─────────────────────────────────────────
    /**
     * Called with the NEW total quantity when the cashier presses + or −.
     * Cascade triggers if the new total exceeds the assigned lot's stock.
     */
    async updateQuantityNumber(newQuantity) {
        if (newQuantity !== null && newQuantity > 0) {
            let line = this.currentOrder?.getSelectedOrderline();
            if (line?.combo_parent_id) line = line.combo_parent_id;

            if (line) {
                const lotName = getLineLot(line);
                const product = line.product_id;

                if (lotName && product?.tracking && product.tracking !== 'none') {
                    const lotStock = getLotStock(this.pos, product.id, lotName);

                    if (lotStock > 0 && newQuantity > lotStock) {
                        // Set to lot stock first, then cascade overflow
                        await super.updateQuantityNumber(lotStock);
                        await this._cascadeToNextLots(line, newQuantity - lotStock);
                        return;
                    }
                }
            }
        }
        return super.updateQuantityNumber(newQuantity);
    },

    // ── Cascade helper ────────────────────────────────────────────────────────
    /**
     * Fills the overflow quantity across subsequent FEFO lots.
     * Called asynchronously from both numpad and +/- paths.
     *
     * @param {Object} sourceLine   The line that was capped
     * @param {number} overflowQty  Units that did not fit in sourceLine's lot
     */
    async _cascadeToNextLots(sourceLine, overflowQty) {
        if (!overflowQty || overflowQty <= 0) return;

        // sourceLine.qty is already capped to lotStock at this point.
        // We pass lotStock + overflow = original requested qty to cascadeLotFill,
        // which re-caps the line (no-op since it's already at lotStock) and
        // then fills the overflow across subsequent FEFO lots.
        const { triggered, addedInfo, missing } = await cascadeLotFill(
            this.pos,
            this.currentOrder,
            sourceLine,
            sourceLine.qty + overflowQty
        );

        if (!triggered) return;

        if (missing > 0) {
            // Not all overflow could be covered by available lots
            this.dialog.add(AlertDialog, {
                title: _t("Lotes insuficientes"),
                body: _t(
                    "%(qty)s unidad(es) no pudieron asignarse a ningún lote con A la mano. "
                    + "Verifica A la mano o selecciona el lote manualmente.",
                    { qty: missing }
                ),
            });
        } else if (addedInfo.length) {
            // Non-blocking toast notification
            const notification = this.env?.services?.notification;
            if (notification) {
                notification.add(
                    _t("A la mano de lote completo. Líneas añadidas: %(info)s",
                        { info: addedInfo.join('  |  ') }),
                    { type: "warning", sticky: false }
                );
            }
        }
    },
});
