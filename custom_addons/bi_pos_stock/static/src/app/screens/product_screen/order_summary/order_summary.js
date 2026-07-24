/** @odoo-module */
/**
 * OrderSummary patch — numpad stock limit enforcement.
 *
 * The existing patches in product_list.js guard the "add product by clicking its card"
 * path (addProductToOrder + addLineToOrder).  However, two more paths bypass those
 * hooks and go directly to PosOrderLine.setQuantity():
 *
 *   A) Numpad value  → OrderSummary._setValue(val)
 *   B) +/- buttons  → OrderSummary.updateQuantityNumber(newQty)
 *
 * Both run inside OrderSummary (a Component), so this.pos is directly accessible.
 * We intercept both to reject any quantity that would exceed the branch stock when
 * pos_allow_order is false.
 */

import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

// ─────────────────────────────────────────────────────────────────────────────
//  Shared helper
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Check whether setting `newQty` on `line` would exceed branch stock.
 * Returns an error object {title, body} if blocked, null otherwise.
 *
 * @param {Object} pos       PosStore service
 * @param {Object} line      PosOrderLine being modified
 * @param {number} newQty    Proposed quantity (after edit)
 * @returns {{title:string, body:string}|null}
 */
function _stockLimitError(pos, line, newQty) {
    if (!pos.config.pos_display_stock) return null;
    if (pos.config.pos_allow_order) return null;
    if (!line.product_id?.is_storable) return null;
    if (newQty <= 0) return null;  // decreasing / removal never blocked by stock

    const product = line.product_id;
    const branchStock = Number(pos.branchStock?.[String(product.id)] ?? 0);

    // Total quantity for this product across all OTHER lines in the order.
    const otherLinesQty = (line.order_id.lines || []).reduce((sum, l) => {
        if (l === line) return sum;
        return l.product_id?.id === product.id ? sum + (l.qty || 0) : sum;
    }, 0);

    const totalWouldBe = otherLinesQty + newQty;

    if (totalWouldBe > branchStock) {
        const allowed = Math.max(0, branchStock - otherLinesQty);
        return {
            title: _t("Límite de A la mano excedido"),
            body: allowed > 0
                ? _t(
                    "%(product)s: hay %(stock)s unidades A la mano en esta sucursal. Puedes agregar como máximo %(allowed)s a esta línea.",
                    { product: product.display_name, stock: branchStock, allowed }
                  )
                : _t(
                    "%(product)s: no queda A la mano en esta sucursal (%(stock)s unidades en total).",
                    { product: product.display_name, stock: branchStock }
                  ),
        };
    }

    return null;
}


// ─────────────────────────────────────────────────────────────────────────────
//  Patch OrderSummary
// ─────────────────────────────────────────────────────────────────────────────

patch(OrderSummary.prototype, {

    /**
     * Path A — Numpad input.
     * _setValue is called for every digit/backspace/Enter from the numpad.
     * The number_buffer service accumulates keystrokes; we receive the final
     * numeric string here as `val` (e.g. "12" or "0.5").
     */
    _setValue(val) {
        if (
            val !== "remove" &&
            this.pos.numpadMode === "quantity"
        ) {
            let selectedLine = this.currentOrder?.getSelectedOrderline();
            if (selectedLine?.combo_parent_id) {
                selectedLine = selectedLine.combo_parent_id;
            }
            if (selectedLine) {
                const newQty = parseFloat(val) || 0;
                const error = _stockLimitError(this.pos, selectedLine, newQty);
                if (error) {
                    this.dialog.add(AlertDialog, error);
                    this.numberBuffer.reset();
                    return;
                }
            }
        }
        return super._setValue(val);
    },

    /**
     * Path B — +/- quantity buttons in the order line row.
     * updateQuantityNumber(newQuantity) is called with the already-computed
     * new total quantity (current ± 1).
     */
    async updateQuantityNumber(newQuantity) {
        if (newQuantity !== null && newQuantity > 0) {
            let selectedLine = this.currentOrder?.getSelectedOrderline();
            if (selectedLine?.combo_parent_id) {
                selectedLine = selectedLine.combo_parent_id;
            }
            if (selectedLine) {
                const error = _stockLimitError(this.pos, selectedLine, newQuantity);
                if (error) {
                    this.dialog.add(AlertDialog, error);
                    return false;
                }
            }
        }
        return super.updateQuantityNumber(newQuantity);
    },
});
