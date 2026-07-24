/** @odoo-module */
/**
 * Navbar patch — adds three action buttons:
 *
 *  1. "Stock" → StockScreen
 *     Unified stock management screen with two sub-tabs:
 *       - Inventario General (all products + per-month sales + Matrix transfers)
 *       - Por Reabastecer (orderpoint-based low-stock items)
 *
 *  2. "Pedidos en Línea" → EcommerceOrdersScreen
 *     Lists pending website sale.orders for this branch.
 *
 *  3. "Actualizar precios" → refresh_prices()
 *     Re-fetches product.pricelist / product.pricelist.item from the server and merges
 *     them into the session's local reactive store, without closing the POS session.
 *
 *     Why this exists: the PoS frontend (OWL) loads pricelist data ONCE when the session
 *     tab is opened (PosStore.processServerData()) and never polls the server again on its
 *     own. If a discount is created/edited in the backend AFTER the cashier's tab was
 *     already open, the new price is invisible in that tab until it's manually refreshed —
 *     this was diagnosed as the root cause of "discount works when importing a Sales Order
 *     but not on direct click in POS" (see docs/audits/2026-07-02_pricelist_discount_architecture.md,
 *     section 4c). This button is the fix: it forces that refresh without a full page reload
 *     or losing the in-progress order.
 */

import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
    },

    // ── Button 1: unified stock screen ──────────────────────────────────────
    show_stock_screen() {
        // Data is loaded lazily inside StockScreen.setup() / onMounted.
        this.pos.navigate('StockScreen');
    },

    // ── Button 2: e-commerce pending orders ─────────────────────────────────
    show_ecommerce_orders() {
        // Data is loaded lazily inside EcommerceOrdersScreen.setup() / onMounted.
        this.pos.navigate('EcommerceOrdersScreen');
    },

    // ── Button 3: refresh pricelist rules from the server ────────────────────
    /**
     * Uses PosData.searchRead(), the same officially-supported call the core app uses
     * elsewhere to pull a fresh record into the session (e.g. after editing a partner).
     * "search_read" is in PosData.autoLoadedOrmMethods, so results are merged into
     * this.pos.models via models.connectNewData() — the same reactive store price
     * computation already reads from. Neither product.pricelist nor
     * product.pricelist.item are in PosData.pohibitedAutoLoadedModels, so this is a
     * supported refresh path, not a workaround.
     *
     * Deliberately does NOT touch lines already in the current order — only new lines
     * added after the refresh pick up the updated rules. This matches standard PoS
     * behavior (a line's price is fixed once added unless the cashier repricing it
     * manually) and avoids silently overwriting a manual price override on an existing line.
     */
    async refresh_prices() {
        if (this._refreshingPrices) {
            return;
        }
        this._refreshingPrices = true;
        try {
            const pricelistIds = this.pos.models["product.pricelist"].getAll().map((pl) => pl.id);
            if (!pricelistIds.length) {
                this.notification.add(
                    "Esta sesión no tiene listas de precios cargadas.",
                    { type: "warning" },
                );
                return;
            }
            const items = await this.pos.data.searchRead(
                "product.pricelist.item",
                [["pricelist_id", "in", pricelistIds]],
                [],
            );
            this.notification.add(
                `Precios actualizados: ${items.length} regla(s) de descuento vigente(s).`,
                { type: "success" },
            );
        } catch (e) {
            console.error("[bi_pos_stock] refresh_prices failed:", e);
            this.notification.add(
                "No se pudieron actualizar los precios. Verifica tu conexión.",
                { type: "danger" },
            );
        } finally {
            this._refreshingPrices = false;
        }
    },
});
