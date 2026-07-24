/** @odoo-module */
/**
 * SelectLotPopup patch — FEFO visual guide + expiry-enriched autocomplete.
 *
 * What this patch adds:
 *
 *  1. FEFO reference table (injected before the lot-container div)
 *     Shows ALL available lots sorted by earliest expiry date with
 *     color-coded "days remaining" badges. Acts as a visual guide so the
 *     cashier always knows which lot to pick first WITHOUT forcing them.
 *
 *  2. Expiry badge on already-selected lot items
 *     After each confirmed lot name in the list, a small coloured badge
 *     shows the expiration date.
 *
 *  3. Enriched autocomplete dropdown labels
 *     Each autocomplete suggestion includes the expiry date and days
 *     remaining, e.g. "LOT001  ·  vence: 31/12/2025 (45d)".
 *
 * All additions are gracefully hidden when:
 *   - the options array is empty (no existing lots)
 *   - expiration_date is null (product_expiry module not installed)
 *
 * The actual lot SELECTION flow is unchanged — this patch is read-only
 * from a data perspective.
 */

import { SelectLotPopup } from "@point_of_sale/app/components/popups/select_lot_popup/select_lot_popup";
import { patch } from "@web/core/utils/patch";
import {
    getDaysLeft,
    getExpiryColorClass,
    formatExpiryDate,
    lotLabelWithExpiry,
} from "../../utils/lot_expiry_utils";

patch(SelectLotPopup.prototype, {

    // ── FEFO guide data ────────────────────────────────────────────────────

    /**
     * All available lots (from props.options) sorted by expiration_date ASC.
     * Lots without a date are pushed to the end.
     * Exposed to the XML template.
     */
    get fefoLots() {
        const opts = this.props.options;
        if (!opts?.length) return [];
        return [...opts].sort((a, b) => {
            if (!a.expiration_date && !b.expiration_date) return 0;
            if (!a.expiration_date) return 1;
            if (!b.expiration_date) return -1;
            return a.expiration_date < b.expiration_date ? -1 : 1;
        });
    },

    /** True if at least one lot has expiration_date data. */
    get hasAnyExpiry() {
        return this.props.options?.some((o) => o.expiration_date) ?? false;
    },

    // ── Helpers for already-selected lot items ─────────────────────────────

    /**
     * Find the expiration_date for a lot by its id.
     * @param {number|string} lotId
     * @returns {string|null}
     */
    getLotExpiry(lotId) {
        return this.props.options?.find((o) => o.id === lotId)?.expiration_date ?? null;
    },

    /**
     * Bootstrap color class for a selected lot.
     * @param {number|string} lotId
     * @returns {string}
     */
    getLotColor(lotId) {
        return getExpiryColorClass(this.getLotExpiry(lotId));
    },

    /**
     * Short formatted expiry label for a selected lot.
     * @param {number|string} lotId
     * @returns {string}
     */
    getLotExpiryLabel(lotId) {
        return formatExpiryDate(this.getLotExpiry(lotId));
    },

    // ── Standalone helpers for XML ─────────────────────────────────────────

    fefoGetDaysLeft: getDaysLeft,
    fefoGetColorClass: getExpiryColorClass,
    fefoFormatDate: formatExpiryDate,

    // ── Autocomplete: enrich option labels with expiry info ────────────────

    getSources() {
        const sources = super.getSources();
        const options = this.props.options ?? [];

        return sources.map((source) => ({
            ...source,
            options: (currentInput) => {
                const raw = source.options(currentInput);
                return raw.map((opt) => {
                    // Try to find the matching original option by label
                    const original = options.find((o) => o.name === opt.label);
                    if (original?.expiration_date) {
                        return {
                            ...opt,
                            label: lotLabelWithExpiry(opt.label, original.expiration_date),
                        };
                    }
                    return opt;
                });
            },
        }));
    },
});
