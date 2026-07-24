/** @odoo-module */
/**
 * PosStore and PosOrder patches for branch-scoped stock
 * and e-commerce order notifications.
 */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { EcommerceOrderPopup } from "../components/ecommerce_order_popup/ecommerce_order_popup";

/**
 * Referencia global al PosStore activo, para código que no es un componente OWL
 * (ej. getters en modelos de datos como PosOrderline) y por lo tanto no puede usar
 * usePos(). Se fija aquí porque processServerData() es lo primero que corre con una
 * instancia de PosStore ya lista. Usado por lot_label_patch.js para leer
 * pos.allLotDetails (fecha de caducidad) desde el getter packLotLines.
 */
let _posStoreRef = null;
export function getPosStoreRef() {
    return _posStoreRef;
}

/**
 * Play a short notification sound.
 *
 * Place your audio file at:
 *   bi_pos_stock/static/src/audio/notification.mp3
 *
 * If the file is not deployed, we MUST avoid issuing the request: when the
 * Odoo PWA Service Worker intercepts a fetch it can't resolve, it surfaces
 * as "Uncaught (in promise) TypeError: Failed to convert value to 'Response'".
 * We HEAD-probe once per page load and only construct Audio if the file
 * is present; the probe response is cached in _audioReady.
 */
const _AUDIO_URL = '/bi_pos_stock/static/src/audio/notification.mp3';
let _audioReady = null;
function playEcommerceSound() {
    if (_audioReady === null) {
        _audioReady = fetch(_AUDIO_URL, { method: 'HEAD', cache: 'no-store' })
            .then((r) => !!(r && r.ok))
            .catch(() => false);
    }
    _audioReady.then((ok) => {
        if (!ok) return;                                        // file not deployed → skip
        try {
            const audio = new Audio(_AUDIO_URL);
            audio.volume = 0.8;
            audio.addEventListener('error', () => {}, { once: true });
            audio.play().catch(() => {});
        } catch (_err) { /* swallow — audio is non-critical */ }
    });
}

patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData();
        _posStoreRef = this;

        // ── Product Line catalog: md.product.line ─────────────────────────────
        // Prefer records already included in the POS bootstrap payload. If the
        // model was not part of the standard model loader, fall back to a
        // direct RPC so the session can still open.
        const loadedProductLine = this.models?.["md.product.line"]?.getAll?.() || [];
        if (loadedProductLine.length) {
            this.productLine = loadedProductLine.map((record) => record.raw || record);
        } else {
            try {
                this.productLine = await this.data.call(
                    "pos.session", "get_product_line_data", [[this.session.id]]
                );
            } catch (e) {
                console.warn("[bi_pos_stock] failed to load md.product.line:", e);
                this.productLine = [];
            }
        }
        this.productLineById = Object.fromEntries(
            this.productLine.map((line) => [String(line.id), line])
        );

        // ── Load all stock data in a SINGLE RPC call ──────────────────────────
        // Previously this was 3 sequential await calls (~600-900ms on slow LAN).
        // get_pos_stock_data() consolidates them into one round-trip.
        if (this.config.pos_display_stock) {
            try {
                const result = await this.data.call(
                    "pos.session", "get_pos_stock_data", [[this.session.id]]
                );
                this.branchStock       = result.branch_stock        ?? {};
                this.branchStockConfig = result.branch_stock_config ?? {};
                this.lotsExpirySummary = result.lots_expiry_summary  ?? {};
                this.allLotDetails     = result.all_lot_details      ?? {};
            } catch (e) {
                console.error("[bi_pos_stock] failed to load pos stock data:", e);
                this.branchStock       = {};
                this.branchStockConfig = {};
                this.lotsExpirySummary = {};
                this.allLotDetails     = {};
            }
        } else {
            this.branchStock       = {};
            this.branchStockConfig = {};
            this.lotsExpirySummary = {};
            this.allLotDetails     = {};
        }

        // Build the product→template lookup map ONCE, cache it for the session.
        // _recomputeStockByTmpl() uses it on every stock tick — must not rebuild it there.
        this._buildProductToTemplateMap();
        this._recomputeStockByTmpl();

        // ── Real-time stock sync via bus ──────────────────────────────────────
        if (this.config.pos_display_stock && !this._branchStockSubscribed) {
            this._branchStockSubscribed = true;
            this.bus.subscribe("BRANCH_STOCK_UPDATED", (payload) => {
                if (payload?.product_id !== undefined && payload?.qty !== undefined) {
                    this.branchStock[String(payload.product_id)] = payload.qty;
                    this._recomputeStockByTmpl();
                    this.bus.trigger("branch-stock-updated", payload.product_id);
                }
            });
        }

        // ── E-commerce order notifications ────────────────────────────────────
        if (!this._ecommerceSubscribed) {
            this._ecommerceSubscribed = true;
            this.bus.subscribe("ECOMMERCE_ORDER", (payload) => {
                if (!payload?.order_name) return;
                playEcommerceSound();
                this.dialog.add(EcommerceOrderPopup, {
                    orderName: payload.order_name,
                    partnerName: payload.partner_name || '',
                    amountTotal: Number(payload.amount_total || 0),
                    currencySymbol: payload.currency_symbol || '$',
                    productCount: Number(payload.product_count || 0),
                });
            });
        }
    },

    /**
     * Build and cache the product.product → product.template lookup map.
     *
     * Called ONCE after processServerData(). The product catalog is static
     * for the duration of a POS session, so there is no reason to rebuild
     * this map on every stock tick.
     */
    _buildProductToTemplateMap() {
        const allProducts = this.models?.["product.product"]?.getAll?.() || [];
        const map = {};
        for (const p of allProducts) {
            const tmplId = p.raw?.product_tmpl_id || p.product_tmpl_id?.id;
            if (tmplId) map[String(p.id)] = Number(tmplId);
        }
        this._productToTmplCache = map;
    },

    /**
     * Build stockByTmplId = { [product_template_id]: qty } from branchStock.
     * Uses the pre-built _productToTmplCache — O(n_stock_entries), not O(all_products).
     */
    _recomputeStockByTmpl() {
        const branchStock = this.branchStock;
        if (!branchStock || !Object.keys(branchStock).length) {
            this.stockByTmplId = {};
            return;
        }

        const map = this._productToTmplCache || {};
        const byTmpl = {};
        for (const [pidStr, qty] of Object.entries(branchStock)) {
            const tmplId = map[pidStr];
            if (!tmplId) continue;
            byTmpl[tmplId] = (byTmpl[tmplId] || 0) + Number(qty);
        }
        this.stockByTmplId = byTmpl;
    },

    getBranchStockForProduct(productId) {
        const base = Number(this.branchStock?.[String(productId)] ?? 0);
        const order = this.getOrder();
        if (!order) return base;
        const ordered = order.lines.reduce((sum, line) => {
            return line.product_id?.id === productId ? sum + (line.qty || 0) : sum;
        }, 0);
        return base - ordered;
    },

    async addLineToOrder(vals, order, configure = true, options = {}) {
        const res = await super.addLineToOrder(vals, order, configure, options);
        const config = this.config;
        if (!config.pos_display_stock) return res;

        // BUG FIX: vals.product_id is undefined in the standard flow because
        // addLineToCurrentOrder passes { product_tmpl_id } not { product_id }.
        // The resolved product.product variant is available on the returned line.
        const product = res?.product_id;
        if (!product?.is_storable) return res;

        const allowOrder = config.pos_allow_order;
        const denyThreshold = Number(config.pos_deny_order) || 0;
        const remainingQty = this.getBranchStockForProduct(product.id);

        let shouldBlock = false;
        if (!allowOrder && remainingQty < 0) {
            shouldBlock = true;
        } else if (allowOrder && denyThreshold > 0 && remainingQty <= denyThreshold) {
            shouldBlock = true;
        }

        if (shouldBlock) {
            const branchStock = Number(this.branchStock?.[String(product.id)] ?? 0);

            // BUG FIX: When addLineToOrder merges with an existing line, `res` is the
            // merged line. Calling removeOrderline(res) would delete ALL units, not just
            // the newly added one. Instead, clamp the line to the available stock.
            const otherLinesQty = (res.order_id?.lines || []).reduce((sum, l) => {
                if (l === res) return sum;
                return l.product_id?.id === product.id ? sum + (l.qty || 0) : sum;
            }, 0);
            const allowedForThisLine = Math.max(0, branchStock - otherLinesQty);

            if (allowedForThisLine <= 0) {
                res.order_id.removeOrderline(res);
            } else {
                res.setQuantity(allowedForThisLine);
            }

            this.dialog.add(AlertDialog, {
                title: _t("Sin A la mano"),
                body: _t(
                    "No se puede agregar %(product)s: A la mano para esta sucursal es %(stock)s unidades.",
                    { product: product.display_name, stock: branchStock }
                ),
            });
        }
        return res;
    },
});

patch(PosOrder.prototype, {
    getOrderedQtyForProduct(productId) {
        return this.lines.reduce((sum, line) => {
            return line.product_id?.id === productId ? sum + (line.qty || 0) : sum;
        }, 0);
    },
});
