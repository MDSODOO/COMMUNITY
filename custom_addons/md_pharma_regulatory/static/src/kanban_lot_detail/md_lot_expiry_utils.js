/** @odoo-module */
/**
 * Duplicado a propósito de bi_pos_stock/static/src/app/utils/lot_expiry_utils.js
 * (getDaysLeft / getExpiryColorClass / formatExpiryDate). No se importa
 * directamente porque ese archivo vive en el bundle del POS
 * (point_of_sale.assets), no en web.assets_backend, y md_pharma_regulatory
 * no depende de bi_pos_stock. Mismo patrón ya usado server-side en
 * product_template.py (MD_LOT_EXPIRY_DANGER_DAYS/WARNING_DAYS replican los
 * mismos umbrales que este archivo, con el mismo comentario de origen).
 *
 * Cualquier cambio de umbrales aquí debe reflejarse también en:
 *   - bi_pos_stock/static/src/app/utils/lot_expiry_utils.js (POS)
 *   - md_pharma_regulatory/models/product_template.py (server, Inventario)
 */

const LOT_EXPIRY_DANGER_DAYS = 30;
const LOT_EXPIRY_WARNING_DAYS = 90;

/** @param {string|null} dateStr @returns {Date|null} */
function parseExpiryDate(dateStr) {
    if (!dateStr) return null;
    const d = new Date(dateStr.replace(' ', 'T'));
    return isNaN(d.getTime()) ? null : d;
}

/** @param {string|null} dateStr @returns {number|null} */
export function getDaysLeft(dateStr) {
    const d = parseExpiryDate(dateStr);
    if (!d) return null;
    return Math.floor((d.getTime() - Date.now()) / 86400000);
}

/** @param {string|null} dateStr @returns {'danger'|'warning'|'success'|'secondary'} */
export function getExpiryColorClass(dateStr) {
    const days = getDaysLeft(dateStr);
    if (days === null) return 'secondary';
    if (days < 0) return 'danger';
    if (days <= LOT_EXPIRY_DANGER_DAYS) return 'danger';
    if (days <= LOT_EXPIRY_WARNING_DAYS) return 'warning';
    return 'success';
}

/** @param {string|null} dateStr @param {string} [locale='es-MX'] @returns {string} */
export function formatExpiryDate(dateStr, locale = 'es-MX') {
    const d = parseExpiryDate(dateStr);
    if (!d) return '';
    return d.toLocaleDateString(locale, { day: '2-digit', month: '2-digit', year: 'numeric' });
}
