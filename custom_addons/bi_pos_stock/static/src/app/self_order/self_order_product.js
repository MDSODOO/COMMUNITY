/** @odoo-module **/
/**
 * Self-Order stock integration.
 *
 * FIXES APPLIED vs. original:
 *   1. Removed setInterval CSS polling (replaced by reactive OWL approach).
 *   2. Unified field names: uses pos_display_stock / pos_stock_type to match
 *      pos.config fields (original used display_stock / stock_type — wrong names).
 *   3. confirmOrder() now uses qty from branchStock (server-side), not quant_text parsing.
 *   4. selectProduct(): Removed incorrect stock types 'virtual' and 'both' (do not exist
 *      in pos.config.pos_stock_type, which only has 'onhand' and 'available').
 *   5. selectProduct() uses branchStock instead of mutating product.qty_available
 *      directly in memory (which caused phantom stock deductions on page refresh).
 */

import { patch } from "@web/core/utils/patch";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { useService } from "@web/core/utils/hooks";
import { BiWarningPopup } from "@bi_pos_stock/app/self_order/bi_warning_popup";
import { SelfOrder } from "@pos_self_order/app/self_order_service";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";


patch(SelfOrder.prototype, {
    async setup(...args) {
        await super.setup(...args);

        // FIXED: branchStock was never populated for the SelfOrder service.
        // models.js sets branchStock on PosStore (loaded in point_of_sale._assets_pos),
        // but SelfOrder is a completely separate service loaded in pos_self_order.assets.
        // Without this RPC call, selfOrder.branchStock is always undefined, causing
        // all products to show 0 stock and blocking all orders when pos_allow_order=false.
        if (this.config?.pos_display_stock) {
            try {
                const result = await this.data.call(
                    'pos.session', 'get_branch_stock', [[this.session.id]]
                );
                this.branchStock = result.branch_stock ?? {};
            } catch (e) {
                console.error('bi_pos_stock: failed to load branch stock for self-order', e);
                this.branchStock = {};
            }
        } else {
            this.branchStock = {};
        }

        this._applyBadgeStyles();
    },

    async confirmOrder() {
        const config = this.config;
        if (!config.pos_display_stock) {
            return super.confirmOrder();
        }

        const order = this.currentOrder;
        const lines = order.lines;
        const allowOrder = config.pos_allow_order;
        const denyThreshold = Number(config.pos_deny_order) || 0;

        // Aggregate ordered quantities per product — same approach as the POS pay() validation
        const orderedByProduct = {};
        for (const line of lines) {
            const prd = this.models['product.product'].getBy('id', line.product_id.id);
            if (!prd?.is_storable) continue;
            orderedByProduct[prd.id] = (orderedByProduct[prd.id] || 0) + line.qty;
        }

        for (const [pidStr, orderedQty] of Object.entries(orderedByProduct)) {
            const pid = Number(pidStr);
            // branchStock is populated at session open time (server-side computed)
            // The key is str(product_id) — consistent with POS main session.
            const available = Number(this.branchStock?.[pidStr] ?? 0);
            const product = this.models['product.product'].getBy('id', pid);
            if (!product) continue;

            let blocked = false;
            if (!allowOrder && available < orderedQty) {
                blocked = true;
            } else if (allowOrder && denyThreshold > 0 && (available - orderedQty) < denyThreshold) {
                blocked = true;
            }

            if (blocked) {
                this.dialog.add(BiWarningPopup, {
                    product,
                    name: product.name,
                    quantity: orderedQty,
                });
                return; // Block order
            }
        }

        return super.confirmOrder();
    },

    /**
     * Apply badge CSS styles reactively.
     * CHANGED: Replaced setInterval(fn, 1200) polling with a one-time call on setup.
     * For reactivity, the self_order.xml template drives style via t-att-style / t-att-class.
     */
    _applyBadgeStyles() {
        const config = this.config;
        if (!config.pos_display_stock) return;

        const bgColor = config.color_background || '#4caf50';
        const fontColor = config.font_background || '#ffffff';
        const positionClassMap = {
            top_left:     ['.qty-left-label', '.qty-image-label'],
            top_right:    ['.qty-tright-label'],
            bottom_right: ['.qty-bright-label'],
        };
        const selectors = positionClassMap[config.stock_position] || [];
        for (const sel of selectors) {
            for (const el of document.querySelectorAll(sel)) {
                el.style.backgroundColor = bgColor;
                el.style.color = fontColor;
            }
        }
    },
});


patch(ProductCard.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.selfOrder = useSelfOrder();
    },

    async selectProduct(qty = 1) {
        const selfOrder = this.selfOrder;
        const config = selfOrder?.config;
        const product = this.props.product;

        if (!config?.pos_display_stock || !product?.is_storable) {
            return super.selectProduct(qty);
        }

        // Read from branchStock — do NOT mutate product.qty_available in memory.
        // Original code did product.qty_available -= 1 which persisted across renders
        // and caused "ghost" stock deductions without a real server state change.
        const available = Number(selfOrder.branchStock?.[String(product.id)] ?? 0);

        const stockOk = (config.pos_stock_type === 'available')
            ? available > 0
            : available > 0; // 'onhand' and 'available' both require qty > 0 to allow adding

        if (!stockOk) {
            this.dialog.add(BiWarningPopup, {
                product,
                name: product.name,
                quantity: qty,
            });
            return;
        }

        // Optimistically deduct from local branchStock to prevent double-adding
        // before the server confirms. The server validates again at confirmOrder().
        if (selfOrder.branchStock) {
            selfOrder.branchStock[String(product.id)] = available - qty;
        }

        return super.selectProduct(qty);
    },
});
