/** @odoo-module */
/**
 * ProductCard extensions for stock badge + lot expiry badge.
 *
 * 1. stockQuantity prop — passed from ProductScreen via XPath position="attributes"
 * 2. get pos() getter — exposes PosStore to the template
 * 3. setup() — hooks dialog + orm services for LotDetailPopup
 * 4. get lotExpiry() — nearest-expiry lot for this product from lotsExpirySummary
 * 5. openLotDetail() — opens LotDetailPopup on-demand
 */

import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { LotDetailPopup } from "../../components/lot_detail_popup/lot_detail_popup";
import { getExpiryColorClass, formatExpiryDate, getDaysLeft } from "../../utils/lot_expiry_utils";

// ── Class-level: declare new props ──────────────────────────────────────────
patch(ProductCard, {
    props: {
        ...ProductCard.props,
        stockQuantity: { type: Number, optional: true },
        // Shape: { lot_name, expiration_date (ISO|null), qty (float|null) } or null.
        // Passed from ProductScreen.state.selectedLotByProductId — see product_list.js.
        selectedLotInfo: { optional: true },
        // true when this product has at least one on-hand lot expiring within
        // SHORT_EXPIRY_DAYS (180 days ≈ 6 months). Injected via ProductScreen
        // XPath using ProductScreen.state.shortExpiryTmplIds — see product_list.js.
        isShortExpiry: { type: Boolean, optional: true },
    },
});

// ── Instance-level: getters + lot detail ────────────────────────────────────
patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },

    /** Exposes PosStore to the XML template without needing usePos() in every patch. */
    get pos() {
        return this.env.services.pos;
    },

    /**
     * Traffic-light CSS class for the stock badge on non-lot products.
     * Red   → qty ≤ 0 (out of stock)
     * Yellow → 0 < qty ≤ pos.config.low_stock threshold
     * Green  → qty > threshold (or threshold is 0/unset)
     */
    get stockColorClass() {
        const qty = this.props.stockQuantity ?? 0;
        const threshold = this.pos.config.low_stock || 0;
        if (qty <= 0) return 'stock-badge-red';
        if (threshold > 0 && qty <= threshold) return 'stock-badge-yellow';
        return 'stock-badge-green';
    },

    /**
     * Returns the nearest-expiry lot summary for this product, or null.
     * Shape: { lot_name, expiration_date, qty }
     */
    get lotExpiry() {
        const productId = this.props.product?.id;
        if (!productId) return null;
        return this.pos.lotsExpirySummary?.[String(productId)] ?? null;
    },

    /** Bootstrap color class for the expiry badge (danger/warning/success/secondary). */
    get lotExpiryColor() {
        return getExpiryColorClass(this.lotExpiry?.expiration_date ?? null);
    },

    /** Days remaining label for the expiry badge, or null if no date. */
    get lotExpiryDays() {
        return getDaysLeft(this.lotExpiry?.expiration_date ?? null);
    },

    /** Formatted expiry date string for display (e.g. "31/12/2025"). */
    get lotExpiryDateLabel() {
        return formatExpiryDate(this.lotExpiry?.expiration_date ?? null);
    },

    /**
     * Reference price shown on the card, e.g. "$65.00".
     *
     * Uses product.template's own displayPriceUnit getter (Odoo core,
     * product_template_accounting.js) — the same tax-config-aware price
     * computation Odoo already uses elsewhere, so we don't duplicate pricing
     * logic here. NOTE: this is the base/list price with taxes applied per
     * pos.config.iface_tax_included, NOT the order's active pricelist price
     * (that is only resolved once the line is actually added to the order) —
     * acceptable for a reference price on the grid card, same tradeoff Odoo
     * itself makes for combo/info displays.
     */
    get displayPrice() {
        return this.props.product?.displayPriceUnit ?? '';
    },

    // ── Selected-lot footer ──────────────────────────────────────────────────
    // props.selectedLotInfo is injected by ProductScreen (product_list.js useEffect)
    // via XPath attribute — same pattern as stockQuantity.  Reading from props
    // guarantees OWL re-renders the card whenever the lot map changes.

    /** Bootstrap color class for the selected lot's expiry badge. */
    get selectedLotExpiryColor() {
        return getExpiryColorClass(this.props.selectedLotInfo?.expiration_date ?? null);
    },

    /** Formatted expiry date of the selected lot, e.g. "31/12/2025". Falls back to "—". */
    get selectedLotDateLabel() {
        const dateStr = this.props.selectedLotInfo?.expiration_date;
        if (!dateStr) return '—';
        return formatExpiryDate(dateStr);
    },

    /** Available qty string for the selected lot. Falls back to "—". */
    get selectedLotQtyLabel() {
        const qty = this.props.selectedLotInfo?.qty;
        if (qty === undefined || qty === null) return '—';
        return String(qty % 1 === 0 ? Math.floor(qty) : qty.toFixed(1));
    },

    /**
     * Opens the LotDetailPopup for this product.
     * Called by the ⓘ button in the template.
     * Uses stopPropagation so it doesn't trigger the card's main onClick.
     */
    openLotDetail(event) {
        event?.stopPropagation();
        const product = this.props.product;
        if (!product?.id) return;
        this.dialog.add(LotDetailPopup, {
            productId: product.id,
            productName: product.display_name || product.name || '',
        });
    },

});
