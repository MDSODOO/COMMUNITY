/** @odoo-module */
/**
 * PosOrderline patch — enable merging lines with the SAME lot while preventing
 * merging lines with DIFFERENT lots.
 *
 * Problem in standard Odoo 19:
 * Standard PosOrderline.prototype.canBeMergedWith includes `!this.isLotTracked()`,
 * which explicitly refuses to merge any lot-tracked product lines. When a cashier
 * scans or adds the same product with the same lot multiple times, Odoo 19 creates
 * multiple duplicate lines for the same lot in the cart instead of incrementing
 * the existing line quantity.
 *
 * Furthermore, a previous attempt patched `can_be_merged_with` (snake_case), which
 * is a legacy method name not used in Odoo 19 (Odoo 19 uses camelCase `canBeMergedWith`).
 *
 * Rules implemented:
 *  - Both lines have the SAME lot  → merge into one line (increment qty)
 *  - Both lines have DIFFERENT lots → keep as separate lines (do not merge)
 *  - One has a lot and the other doesn't → keep as separate lines
 *  - Non-lot-tracked products      → delegate to standard super.canBeMergedWith()
 */

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

/**
 * Returns the first lot_name assigned to a line, or null if none.
 * `pack_lot_ids` is the array of PackLot objects on a PosOrderline.
 * Each PackLot has a `lot_name` string property.
 */
function getLineLotName(line) {
    if (!line.pack_lot_ids || line.pack_lot_ids.length === 0) return null;
    return line.pack_lot_ids[0]?.lot_name || null;
}

patch(PosOrderline.prototype, {
    canBeMergedWith(orderline) {
        if (this.isLotTracked() || orderline.isLotTracked()) {
            const thisLot = getLineLotName(this);
            const otherLot = getLineLotName(orderline);

            // If neither has a lot yet or lots differ, do not merge
            if (!thisLot || !otherLot || thisLot !== otherLot) {
                return false;
            }

            // Both lines have the exact same lot: verify standard non-lot merge criteria
            const ProductPrice = this.models["decimal.precision"].find(
                (dp) => dp.name === "Product Price"
            );
            const price = ProductPrice.round(this.price_unit || 0);
            const product = orderline.getProduct();
            const order_line_price = product.getPrice(
                orderline.order_id.pricelist_id,
                this.getQuantity(),
                0,
                false,
                product
            );

            const isSameCustomerNote =
                (Boolean(orderline.getCustomerNote()) === false &&
                    Boolean(this.getCustomerNote()) === false) ||
                orderline.getCustomerNote() === this.getCustomerNote();

            return (
                orderline.getNote() === this.getNote() &&
                this.getProduct().id === orderline.getProduct().id &&
                this.isPosGroupable() &&
                this.getDiscount() === orderline.getDiscount() &&
                this.price_type === orderline.price_type &&
                this.currency.isZero(
                    this.currency.round(price) -
                        this.currency.round(order_line_price) -
                        orderline.getPriceExtra()
                ) &&
                this.full_product_name === orderline.full_product_name &&
                isSameCustomerNote &&
                !this.refunded_orderline_id &&
                !orderline.isPartOfCombo()
            );
        }

        return super.canBeMergedWith(orderline);
    },
});
