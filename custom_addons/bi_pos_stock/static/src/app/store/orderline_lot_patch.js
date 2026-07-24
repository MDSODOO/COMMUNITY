/** @odoo-module */
/**
 * PosOrderline patch — prevent merging lines with different lots.
 *
 * Standard POS behavior merges any two lines for the same product into one
 * (incrementing qty). This is wrong when a cashier picks a *different* lot:
 * the new lot gets silently swallowed by the existing line, making it
 * impossible to sell the same product from two distinct lots in one order.
 *
 * Fix: override `can_be_merged_with` so that two lines with different
 * lot assignments are always treated as separate lines.
 *
 * Rules:
 *  - Both lines have NO lot  → merge normally (unchanged behavior)
 *  - Both lines have the SAME lot → merge normally
 *  - One has a lot and the other doesn't → new line (different lots)
 *  - Both have DIFFERENT lots → new line
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
    can_be_merged_with(orderline) {
        // Let the base class do its standard checks first (same product,
        // same price, no note, etc.). If it already blocks, respect that.
        const baseResult = super.can_be_merged_with(orderline);
        if (!baseResult) return false;

        const thisLot = getLineLotName(this);
        const otherLot = getLineLotName(orderline);

        // Different lot assignment → always create a new line
        if (thisLot !== otherLot) {
            return false;
        }

        return true;
    },
});
