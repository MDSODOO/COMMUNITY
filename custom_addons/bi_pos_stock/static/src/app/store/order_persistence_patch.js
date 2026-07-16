/** @odoo-module */
/**
 * Order Persistence Patch — protects open orders against screensaver / tab-hide events.
 *
 * Problem:
 *   Odoo 19 POS persists orders to IndexedDB lazily (on payment, order switch, etc.).
 *   When the OS screensaver activates or the browser hides the tab, in-flight reactive
 *   state may never reach IndexedDB — causing the active order to appear empty when the
 *   cashier returns.
 *
 * Solution:
 *   Listen to 'visibilitychange' (hidden) and 'pagehide' events and force-save all
 *   open draft orders to IndexedDB using Odoo's own pos.db layer.
 *
 * Design notes:
 *   - Uses document.visibilityState rather than window blur/focus because blur fires
 *     on every iframe interaction and creates unnecessary IDB writes.
 *   - pagehide covers mobile browsers where unload is unreliable.
 *   - All saves are fire-and-forget: if IDB is unavailable (private mode) the error
 *     is caught silently — we never block the UI for a persistence side-effect.
 */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    /**
     * Called by Odoo's service framework when PosStore is fully initialized
     * and the session is ready. Safe to register DOM listeners here.
     */
    async ready() {
        await super.ready(...arguments);
        this._registerOrderPersistenceListeners();
    },

    _registerOrderPersistenceListeners() {
        // Bind once and store reference so we can cleanly remove them on destroy.
        this._onVisibilityChangeBound = this._onVisibilityChange.bind(this);
        this._onPageHideBound         = this._flushOpenOrdersToIDB.bind(this);

        document.addEventListener('visibilitychange', this._onVisibilityChangeBound);
        window.addEventListener('pagehide',           this._onPageHideBound);
    },

    _onVisibilityChange() {
        if (document.visibilityState === 'hidden') {
            this._flushOpenOrdersToIDB();
        }
    },

    /**
     * Force-save all draft orders with lines to IndexedDB.
     *
     * Uses Odoo's internal pos.db.save_unpaid_order() which is the same
     * codepath triggered normally when the cashier switches orders.
     * Calling it explicitly here ensures the IDB state is current before
     * the browser suspends the tab.
     */
    _flushOpenOrdersToIDB() {
        try {
            const orders = this.models?.['pos.order']?.getAll?.() ?? [];
            let count = 0;
            for (const order of orders) {
                // Only persist open (draft) orders that actually have lines.
                // Skipping empty orders avoids polluting IDB with blank entries.
                if (order.state === 'draft' && order.lines?.length > 0) {
                    this.db?.save_unpaid_order?.(order);
                    count++;
                }
            }
            if (count > 0) {
                // Use debug level — this fires on every screensaver, no need to
                // clutter the production console with info-level messages.
                console.debug(`[bi_pos_stock] Flushed ${count} order(s) to IDB (visibilitychange).`);
            }
        } catch (err) {
            // Never surface errors from a persistence side-effect to the UI.
            console.warn('[bi_pos_stock] Could not flush orders to IDB:', err);
        }
    },

    /**
     * Clean up DOM listeners when PosStore is destroyed (logout / session close).
     * Without this, the listener would reference a dead PosStore and leak memory.
     */
    destroy() {
        if (this._onVisibilityChangeBound) {
            document.removeEventListener('visibilitychange', this._onVisibilityChangeBound);
        }
        if (this._onPageHideBound) {
            window.removeEventListener('pagehide', this._onPageHideBound);
        }
        super.destroy?.(...arguments);
    },
});
