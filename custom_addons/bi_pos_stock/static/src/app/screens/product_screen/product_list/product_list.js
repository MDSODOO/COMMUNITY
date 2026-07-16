/** @odoo-module **/
/**
 * ProductScreen and PosStore patches — branch stock display and validation.
 *
 * Badge architecture follows the same pattern as core Odoo's productCartQty:
 *   1. ProductScreen.state.stockByProductTmplId holds {tmpl_id: qty}
 *   2. useEffect keeps it in sync with pos.stockByTmplId + order lines
 *   3. The ProductScreen XML template (extended via XPath) passes
 *      stockQuantity prop to ProductCard
 *   4. ProductCard renders the badge using that prop
 */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { useState, useEffect } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { isShortExpiry } from "../../../utils/lot_expiry_utils";


// ---------------------------------------------------------------------------
// PosStore.pay() — payment-time stock validation
// ---------------------------------------------------------------------------
patch(PosStore.prototype, {
    async pay() {
        const config = this.config;
        if (!config.pos_display_stock) {
            return super.pay();
        }

        const order = this.getOrder();
        const lines = order.getOrderlines();
        const allowOrder = config.pos_allow_order;
        const denyThreshold = Number(config.pos_deny_order) || 0;

        const orderedByProduct = {};
        for (const line of lines) {
            const product = line.product_id;
            if (!product?.is_storable) continue;
            const pid = product.id;
            orderedByProduct[pid] = (orderedByProduct[pid] || 0) + (line.qty || 0);
        }

        for (const [pidStr, orderedQty] of Object.entries(orderedByProduct)) {
            const pid = Number(pidStr);
            const available = Number(this.branchStock?.[pidStr] ?? 0);
            const product = this.models["product.product"].getBy("id", pid);
            if (!product) continue;

            let blocked = false;
            if (!allowOrder && available < orderedQty) {
                blocked = true;
            } else if (allowOrder && denyThreshold > 0 && (available - orderedQty) < denyThreshold) {
                blocked = true;
            }

            if (blocked) {
                this.dialog.add(AlertDialog, {
                    title: _t("Validación de A la mano fallida"),
                    body: _t(
                        "No se puede completar el pedido: %(product)s tiene %(available)s unidades A la mano en esta sucursal y se pidieron %(ordered)s.",
                        { product: product.display_name, available, ordered: orderedQty }
                    ),
                });
                return;
            }
        }

        return super.pay();
    },
});


// ---------------------------------------------------------------------------
// ProductScreen — state management and per-click validation
// ---------------------------------------------------------------------------
patch(ProductScreen.prototype, {
    setup() {
        super.setup();

        // Mirror core pattern (quantityByProductTmplId): extend the existing
        // reactive state object with our stock map. Do NOT call useState() again —
        // that would register a second hook at a different index, causing OWL
        // lifecycle errors. Adding a property to the existing state proxy IS
        // reactive in OWL 2.x.
        this.state.stockByProductTmplId = {};
        // { [product_id]: { lot_name, expiration_date, qty } | null }
        // Populated whenever a lot is assigned to an order line.
        this.state.selectedLotByProductId = {};

        // Sync state whenever PosStore's stockByTmplId changes OR the SET of products
        // in the order changes. Using a product-ID fingerprint instead of totalQuantity
        // avoids re-running (and re-allocating { ...base }) on every qty spinner click
        // when the cashier is just adjusting a quantity of an already-present product.
        useEffect(
            () => {
                if (!this.pos.config.pos_display_stock) {
                    return;
                }

                const base = this.pos.stockByTmplId || {};

                // Deduct in-cart quantities per template (same as quantityByProductTmplId)
                const deducted = { ...base };
                const lines = this.currentOrder?.lines || [];
                for (const line of lines) {
                    if (line.combo_parent_id) continue;
                    const tmplId = line.product_id?.product_tmpl_id?.id;
                    if (tmplId && tmplId in deducted) {
                        deducted[tmplId] = (deducted[tmplId] || 0) - (line.qty || 0);
                    }
                }

                this.state.stockByProductTmplId = deducted;
            },
            () => [
                // Re-run when server stock changes
                this.pos.stockByTmplId,
                // Re-run when the active order switches
                this.currentOrder,
                // Re-run only when products in the order change (added/removed),
                // NOT on every qty change — avoids expensive re-renders on spinner clicks.
                this.currentOrder?.lines
                    ?.map(l => `${l.product_id?.product_tmpl_id?.id}:${l.qty ?? 0}`)
                    .join('|') ?? '',
            ]
        );

        // ── Short-expiry prioritization map ────────────────────────────────────
        // Rebuilt whenever lotsExpirySummary changes (typically once at session
        // open, then stays static). Stored as a plain array so OWL reactivity
        // detects the replacement assignment (Set is not deeply reactive in OWL).
        //
        // Product cards read this via the isShortExpiry prop injected through the
        // ProductScreen XPath in product_card.xml — same pattern as stockQuantity.
        this.state.shortExpiryTmplIds = [];

        useEffect(
            () => {
                const summary = this.pos.lotsExpirySummary;
                if (!summary || !Object.keys(summary).length) {
                    this.state.shortExpiryTmplIds = [];
                    return;
                }
                const critical = [];
                for (const [tmplIdStr, lot] of Object.entries(summary)) {
                    if (isShortExpiry(lot.expiration_date)) {
                        critical.push(Number(tmplIdStr));
                    }
                }
                this.state.shortExpiryTmplIds = critical;
            },
            () => [this.pos.lotsExpirySummary],
        );

        // ── Selected-lot map ─────────────────────────────────────────────────
        // Rebuilds whenever the set of confirmed lot names on any order line
        // changes.  The dep string "lot|names|..." changes on every assignment
        // so OWL triggers a re-run and ProductCard re-renders with the new prop.
        useEffect(
            () => {
                const lines = this.currentOrder?.lines || [];
                const lotMap = {};
                for (const line of lines) {
                    const product = line.product_id;  // product.product record
                    if (!product?.tracking || product.tracking === 'none') continue;
                    // pack_lot_ids is One2many to pos.pack.operation.lot (lot_name field)
                    const lotName = line.pack_lot_ids?.[0]?.lot_name;
                    if (!lotName) continue;
                    // allLotDetails is keyed by "{product.product.id}_{lot_name}"
                    const detail = this.pos.allLotDetails?.[`${product.id}_${lotName}`];
                    // Key the map by template ID — the ProductScreen loop iterates
                    // product.template records, so product.id in the XPath is template.id.
                    const tmplId = product.product_tmpl_id?.id;
                    if (!tmplId) continue;
                    lotMap[tmplId] = detail
                        ? { lot_name: lotName, expiration_date: detail.expiration_date, qty: detail.qty }
                        : { lot_name: lotName, expiration_date: null, qty: null };
                }
                this.state.selectedLotByProductId = lotMap;
            },
            () => [
                this.currentOrder,
                // String fingerprint that changes on any lot name assignment
                this.currentOrder?.lines
                    ?.map(l => l.pack_lot_ids?.[0]?.lot_name ?? '')
                    .join('|') ?? '',
            ]
        );
    },

    /**
     * Override ProductScreen.products getter to sort by nearest lot expiry date.
     *
     * Sort order:
     *   1. Products with a tracked lot in stock → sorted by expiration_date ASC
     *      (nearest-to-expire first, including already-expired lots).
     *   2. Products with no expiry data (no lot tracking or no quants) → last,
     *      in the original server order (no extra alphabetical sort applied).
     *
     * Data source: this.pos.lotsExpirySummary — loaded once at session open via
     * get_lots_expiry_summary(), keyed by str(product.template.id).
     * ISO UTC date strings are lexicographically comparable, so string comparison
     * is sufficient and avoids constructing Date objects on every sort tick.
     *
     * Falls back to the original order if lotsExpirySummary is empty (e.g. when
     * the POS is not configured to track lots, or no lots are in stock).
     */
    get products() {
        const base = super.products;
        const summary = this.pos.lotsExpirySummary;
        if (!summary || !Object.keys(summary).length) return base;

        return [...base].sort((a, b) => {
            const aExp = summary[String(a.id)]?.expiration_date ?? null;
            const bExp = summary[String(b.id)]?.expiration_date ?? null;

            if (aExp && bExp) {
                if (aExp < bExp) return -1;
                if (aExp > bExp) return 1;
                return 0;
            }
            if (aExp) return -1;  // a has expiry, b does not → a first
            if (bExp) return 1;   // b has expiry, a does not → b first
            return 0;             // neither has expiry → keep original order
        });
    },

    addProductToOrder(product) {
        const config = this.pos.config;

        if (!config.pos_display_stock || product.type === "service" || !product.is_storable) {
            return super.addProductToOrder(product);
        }

        const stock = this.state.stockByProductTmplId?.[product.id] ?? 0;

        if (!config.pos_allow_order && stock <= 0) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Sin A la mano"),
                body: _t(
                    "%(product)s no tiene A la mano en esta sucursal.",
                    { product: product.display_name }
                ),
            });
            return;
        }

        return super.addProductToOrder(product);
    },
});
