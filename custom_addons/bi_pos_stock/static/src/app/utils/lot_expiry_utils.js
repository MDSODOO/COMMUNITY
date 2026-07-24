/** @odoo-module */
/**
 * Shared utilities for lot expiration date display.
 *
 * Used by:
 *   - ProductCard (expiry badge)
 *   - SelectLotPopup patch (FEFO guide + autocomplete labels)
 *   - LotDetailPopup (full breakdown table)
 *
 * Color thresholds (tuneable):
 *   Red    — expired OR ≤ 30 days remaining
 *   Orange — 31 – 90 days remaining
 *   Green  — > 90 days remaining
 *   Grey   — no expiration date recorded
 */

/**
 * Parse an expiration date string to a JS Date.
 * Handles both ISO-8601 ("2025-12-31T23:59:59Z") and legacy Odoo
 * datetime strings ("2025-12-31 23:59:59").
 *
 * @param {string|null} dateStr
 * @returns {Date|null}
 */
export function parseExpiryDate(dateStr) {
    if (!dateStr) return null;
    const d = new Date(dateStr.replace(' ', 'T'));
    return isNaN(d.getTime()) ? null : d;
}

/**
 * Number of whole days remaining until expiration.
 * Negative means already expired.
 *
 * @param {string|null} dateStr
 * @returns {number|null}
 */
export function getDaysLeft(dateStr) {
    const d = parseExpiryDate(dateStr);
    if (!d) return null;
    return Math.floor((d.getTime() - Date.now()) / 86400000);
}

/**
 * Bootstrap contextual color class based on days remaining.
 *
 * @param {string|null} dateStr
 * @returns {'danger'|'warning'|'success'|'secondary'}
 */
export function getExpiryColorClass(dateStr) {
    const days = getDaysLeft(dateStr);
    if (days === null) return 'secondary';   // no date → grey
    if (days < 0)      return 'danger';      // already expired
    if (days <= 30)    return 'danger';      // ≤ 30 days
    if (days <= 90)    return 'warning';     // 31–90 days
    return 'success';                        // > 90 days
}

/**
 * Human-readable expiration label.
 * Format: "31/12/2025"
 *
 * @param {string|null} dateStr
 * @param {string} [locale='es-MX']
 * @returns {string}
 */
export function formatExpiryDate(dateStr, locale = 'es-MX') {
    const d = parseExpiryDate(dateStr);
    if (!d) return '';
    return d.toLocaleDateString(locale, {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
    });
}

/**
 * Short label for autocomplete dropdowns: "LOT001 — 31/12/25 (45d)"
 * Used to enrich lot names in the SelectLotPopup autocomplete.
 *
 * @param {string} lotName
 * @param {string|null} dateStr
 * @returns {string}
 */
export function lotLabelWithExpiry(lotName, dateStr) {
    if (!dateStr) return lotName;
    const days = getDaysLeft(dateStr);
    const dateLabel = formatExpiryDate(dateStr);
    const daysPart = days !== null
        ? ` (${days >= 0 ? days + 'd' : 'VENCIDO'})`
        : '';
    return `${lotName}  ·  vence: ${dateLabel}${daysPart}`;
}

/**
 * Days threshold for "short expiry" highlighting.
 * 180 days ≈ 6 months — products expiring within this window get a
 * purple border on the product card and are sorted to the top of the grid.
 */
export const SHORT_EXPIRY_DAYS = 180;

/**
 * Returns true if the lot expires within SHORT_EXPIRY_DAYS from now.
 * Already-expired lots (days < 0) are also considered "short expiry" so
 * they are always visible and can be acted upon.
 *
 * @param {string|null} dateStr
 * @returns {boolean}
 */
export function isShortExpiry(dateStr) {
    const days = getDaysLeft(dateStr);
    if (days === null) return false;   // no expiry date recorded → not critical
    return days <= SHORT_EXPIRY_DAYS;
}

/**
 * Format a quantity for display: whole numbers with no decimals, otherwise
 * 2 decimal places. Used anywhere a raw qty (line.qty, a summed qty, etc.)
 * needs a short label (ticket lot lines, receipt merge, etc.).
 *
 * @param {number} qty
 * @returns {string}
 */
export function formatQty(qty) {
    return Number.isInteger(qty) ? String(qty) : qty.toFixed(2);
}
