/** @odoo-module */
/**
 * Shared FEFO lot/stock helpers — single source of truth for anything that
 * reads pos.allLotDetails or assigns a lot to an order line.
 *
 * Extracted from lot_cascade_patch.js (where this logic first appeared for the
 * numpad/+- overflow cascade) so that LotSelectionPopup — the new "click card
 * to pick lots" popup — reads/writes the EXACT same cached data and the same
 * line-assignment primitive. Two independent implementations of "what lots
 * does this product have, FEFO-sorted" would drift apart the first time one
 * of them is tuned (e.g. a rounding fix) and not the other.
 *
 * Data source: pos.allLotDetails, preloaded once at session open by
 * get_all_lot_details() (bi_pos_lots.py). Key format:
 *   "{product.product.id}_{lot_name}" -> { product_id, qty, expiration_date }
 * NOTE the key is the product.product (variant) id, NOT product.template id —
 * see getFefoLotsForTemplate() below for the template-level convenience used
 * by ProductScreen (which iterates product.template records).
 */

/**
 * Return the total available qty for a specific lot of a product.product.
 * Returns Infinity when the lot is not tracked / data is absent (callers use
 * this as a "never block/cascade" signal).
 *
 * @param {Object} pos - PosStore instance
 * @param {number} productId - product.product id
 * @param {string|null} lotName
 * @returns {number}
 */
export function getLotStock(pos, productId, lotName) {
    if (!lotName || !pos.allLotDetails) return Infinity;
    const key = `${productId}_${lotName}`;
    const qty = pos.allLotDetails[key]?.qty;
    return qty !== undefined ? Number(qty) : 0;
}

/**
 * Return all lots for one product.product id, sorted FEFO (earliest expiry
 * first; lots without a date pushed to the end). Only lots with qty > 0.
 *
 * @param {Object} pos - PosStore instance
 * @param {number} productId - product.product id
 * @returns {Array<{lot_name:string, qty:number, expiration_date:string|null}>}
 */
export function getFefoLots(pos, productId) {
    const details = pos.allLotDetails || {};
    const pid = String(productId);
    const lots = [];

    for (const [key, detail] of Object.entries(details)) {
        if (String(detail.product_id) !== pid) continue;
        if (!detail.qty || detail.qty <= 0) continue;
        // Strip the "{pid}_" prefix to recover the lot name — safe even when
        // lot names themselves contain underscores.
        const lot_name = key.slice(pid.length + 1);
        lots.push({
            lot_name,
            qty: detail.qty,
            expiration_date: detail.expiration_date,
        });
    }

    return sortFefo(lots);
}

/** Shared FEFO comparator: earliest expiry first, null dates last. */
function sortFefo(lots) {
    return lots.sort((a, b) => {
        if (!a.expiration_date && !b.expiration_date) return 0;
        if (!a.expiration_date) return 1;
        if (!b.expiration_date) return -1;
        return a.expiration_date < b.expiration_date ? -1 : 1;
    });
}

/**
 * All lots across every variant of a product.template, sorted FEFO.
 *
 * Used by LotSelectionPopup: ProductScreen's grid loop works with
 * product.template records (see bi_pos_stock.ProductScreen XPath in
 * product_card.xml), but pos.allLotDetails is keyed by product.product
 * (variant) id. Most products in this catalog are single-variant, but we
 * aggregate across all variants for correctness (mirrors the server-side
 * get_product_lots_detail(), which resolves template -> product_variant_ids).
 *
 * Each returned lot carries:
 *   - productId: the variant it belongs to (which product.product to add to
 *     the order for that lot)
 *   - key: "{productId}_{lot_name}" — same composite format as the
 *     allLotDetails key. Callers should use this (not lot_name alone) to key
 *     any per-lot UI state, since two different variants of a multi-variant
 *     template could in theory reuse the same textual lot code.
 *
 * @param {Object} pos - PosStore instance
 * @param {number[]} variantIds - product.product ids belonging to the template
 * @returns {Array<{lot_name:string, qty:number, expiration_date:string|null, productId:number, key:string}>}
 */
export function getFefoLotsForTemplate(pos, variantIds) {
    const combined = [];
    for (const vid of variantIds || []) {
        for (const lot of getFefoLots(pos, vid)) {
            combined.push({ ...lot, productId: vid, key: `${vid}_${lot.lot_name}` });
        }
    }
    return sortFefo(combined);
}

/**
 * Assign a single lot to an orderline, replacing any previously assigned lot.
 *
 * Uses the official PosOrderline.setPackLotLines() API (Odoo 16+, maintained
 * through 17/18/19):
 *   setPackLotLines({ modifiedPackLotLines, newPackLotLines, removedPackLotLines })
 * Each pack_lot record carries a client-side `cid` (UUID) used for removal.
 *
 * @param {Object} line - PosOrderline
 * @param {string} lotName
 */
export function assignLotToLine(line, lotName) {
    if (!line || !lotName) return;
    if (typeof line.setPackLotLines !== 'function') {
        // Defensive fallback — should never happen in Odoo 17+
        console.warn('[bi_pos_stock] setPackLotLines not available on line', line);
        return;
    }

    const removedPackLotLines = (line.pack_lot_ids || [])
        .map((plo) => ({ cid: plo.cid }))
        .filter((r) => r.cid);

    line.setPackLotLines({
        modifiedPackLotLines: [],
        newPackLotLines: [{ lot_name: lotName }],
        removedPackLotLines,
    });
}
