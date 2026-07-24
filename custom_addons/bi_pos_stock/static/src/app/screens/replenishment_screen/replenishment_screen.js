/** @odoo-module */
/**
 * StockScreen — Unified stock management screen.
 *
 * Two sub-tabs:
 *   1. "Inventario General" — All storable POS products with per-month sales
 *      (3 separate month columns) and "Solicitar" button to create internal
 *      transfers from the Matrix warehouse.
 *
 *   2. "Por Reabastecer" — Orderpoint-based products where on-hand ≤ min_qty.
 *      "Solicitar" button creates transfers from the local warehouse.
 *
 * Data is fetched on mount via two RPC calls:
 *   - pos.session.get_quarterly_inventory()  → Inventario General
 *   - pos.session.get_replenishment_data()   → Por Reabastecer
 *
 * Registered in "pos_pages" (Odoo 19 screen registry).
 */

import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted } from "@odoo/owl";
import { ReplenishmentLine } from "./replenishment_line/replenishment_line";

export class StockScreen extends Component {
    static components = { ReplenishmentLine };
    static template = "bi_pos_stock.StockScreen";
    static props = {};
    static storeOnOrder = false;

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            activeTab: 'inventory',  // 'inventory' | 'restock'
            // Inventario General
            inventoryProducts: [],
            monthNames: [],
            bfLabel: null,           // ej. "26 May 2026" — null si no hay snapshot activo
            loadingInventory: false,
            // Por Reabastecer
            restockProducts: [],
            loadingRestock: false,
            // Set of IDs currently being requested (prevents double-click)
            requestingInventory: new Set(),  // product_ids
            requestingRestock: new Set(),    // orderpoint_ids
        });

        onMounted(() => this._loadAll());
    }

    async _loadAll() {
        await Promise.all([
            this._loadInventory(),
            this._loadRestock(),
        ]);
    }

    async _loadInventory() {
        this.state.loadingInventory = true;
        try {
            const result = await this.orm.call(
                'pos.session',
                'get_quarterly_inventory',
                [[this.pos.session.id]],
            );
            this.state.inventoryProducts = (result.products || []).map((product) =>
                this._withLineName(product)
            );
            this.state.monthNames = result.month_names || ['Mes 1', 'Mes 2', 'Mes 3'];
            this.state.bfLabel = result.bf_label || null;
        } catch (err) {
            console.error('[bi_pos_stock] Failed to load quarterly inventory:', err);
            this.notification.add(
                'No se pudo cargar el inventario. Intenta de nuevo.',
                { type: 'danger', sticky: false },
            );
        } finally {
            this.state.loadingInventory = false;
        }
    }

    async _loadRestock() {
        this.state.loadingRestock = true;
        try {
            const products = await this.orm.call(
                'pos.session',
                'get_replenishment_data',
                [[this.pos.session.id]],
            );
            this.state.restockProducts = products;
        } catch (err) {
            console.error('[bi_pos_stock] Failed to load replenishment data:', err);
            this.notification.add(
                'No se pudo cargar los datos de reabastecimiento. Intenta de nuevo.',
                { type: 'danger', sticky: false },
            );
        } finally {
            this.state.loadingRestock = false;
        }
    }

    back() {
        this.pos.navigate('ProductScreen', { orderUuid: this.pos.selectedOrderUuid });
    }

    switchTab(tab) {
        this.state.activeTab = tab;
    }

    // ── Excel Export ──────────────────────────────────────────────────────────

    /**
     * Export the currently visible tab to Excel (.xlsx) via backend RPC.
     *
     * Flow:
     *   1. Calls pos.session.export_stock_xlsx(tab) on the backend.
     *   2. Backend generates an openpyxl workbook with styled headers + data.
     *   3. Returns base64-encoded xlsx → frontend decodes and triggers download.
     */
    async exportExcel() {
        const tab = this.isInventoryTab ? 'inventory' : 'restock';
        const tabLabel = this.isInventoryTab ? 'Inventario General' : 'Por Reabastecer';

        try {
            this.notification.add(
                `Generando Excel de "${tabLabel}"…`,
                { type: 'info', sticky: false },
            );

            const result = await this.orm.call(
                'pos.session',
                'export_stock_xlsx',
                [[this.pos.session.id], tab],
            );

            if (!result || !result.data) {
                this.notification.add(
                    'No se generaron datos para exportar.',
                    { type: 'warning', sticky: false },
                );
                return;
            }

            // Decode base64 → Blob → download
            const byteCharacters = atob(result.data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], {
                type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            });

            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = result.filename || 'stock_export.xlsx';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            this.notification.add(
                `Excel "${result.filename}" descargado correctamente.`,
                { type: 'success', sticky: false },
            );
        } catch (err) {
            console.error('[bi_pos_stock] exportExcel error:', err);
            this.notification.add(
                'Error al generar el archivo Excel. Intenta de nuevo.',
                { type: 'danger', sticky: false },
            );
        }
    }

    // ── Getters ──────────────────────────────────────────────────────────────

    get isInventoryTab() {
        return this.state.activeTab === 'inventory';
    }

    get isRestockTab() {
        return this.state.activeTab === 'restock';
    }

    get inventoryProducts() {
        return this.state.inventoryProducts;
    }

    get restockProducts() {
        return this.state.restockProducts;
    }

    get monthNames() {
        return this.state.monthNames.length ? this.state.monthNames : ['Mes 1', 'Mes 2', 'Mes 3'];
    }

    get bfLabel() {
        return this.state.bfLabel;
    }

    get restockCount() {
        return this.state.restockProducts.length;
    }

    isRequestingInventory(productId) {
        return this.state.requestingInventory.has(productId);
    }

    isRequestingRestock(orderpointId) {
        return this.state.requestingRestock.has(orderpointId);
    }

    formatQty(value) {
        return Number(value || 0).toFixed(0);
    }

    _withLineName(product) {
        if (product.line_name || !product.line_id) {
            return product;
        }
        const line = this.pos.productLineById?.[String(product.line_id)];
        const lineName = line?.display_name || line?.name || '';
        return { ...product, line_name: lineName };
    }

    // ── Actions ──────────────────────────────────────────────────────────────

    /**
     * Inventario General: request transfer from Matrix warehouse.
     * Qty = sum of 3 months sales (rounded up), min 1.
     */
    async requestInventoryReplenishment(product) {
        const { product_id, name, month1_sales, month2_sales, month3_sales } = product;

        if (this.state.requestingInventory.has(product_id)) {
            return;
        }

        const totalSales = (month1_sales || 0) + (month2_sales || 0) + (month3_sales || 0);
        const qty = Math.max(Math.ceil(totalSales || 1), 1);

        this.state.requestingInventory = new Set([...this.state.requestingInventory, product_id]);

        try {
            const result = await this.orm.call(
                'pos.session',
                'create_inventory_replenishment',
                [[this.pos.session.id], product_id, qty],
            );

            if (result.success) {
                this.notification.add(
                    `Transferencia ${result.picking_name} creada: `
                    + `${this.formatQty(result.qty)} uds. de "${result.product_name}" solicitadas a la Matriz.`,
                    { type: 'success', sticky: false },
                );
                const updated = this.state.inventoryProducts.map((p) =>
                    p.product_id === product_id ? { ...p, _requested: true } : p
                );
                this.state.inventoryProducts = updated;
            } else {
                this.notification.add(
                    result.message || 'Error al crear la transferencia.',
                    { type: 'warning', sticky: false },
                );
            }
        } catch (err) {
            this.notification.add(
                `Error inesperado al solicitar reabastecimiento de "${name}".`,
                { type: 'danger', sticky: false },
            );
            console.error('[bi_pos_stock] requestInventoryReplenishment error:', err);
        } finally {
            const next = new Set(this.state.requestingInventory);
            next.delete(product_id);
            this.state.requestingInventory = next;
        }
    }

    /**
     * Por Reabastecer: request transfer from local warehouse (orderpoint).
     */
    async requestRestockReplenishment(product) {
        const { orderpoint_id, display_name } = product;

        if (this.state.requestingRestock.has(orderpoint_id)) {
            return;
        }

        this.state.requestingRestock = new Set([...this.state.requestingRestock, orderpoint_id]);

        try {
            const result = await this.orm.call(
                'pos.session',
                'create_replenishment_transfer',
                [[this.pos.session.id], orderpoint_id],
            );

            if (result.success) {
                this.state.restockProducts = this.state.restockProducts.filter(
                    (p) => p.orderpoint_id !== orderpoint_id,
                );
                this.notification.add(
                    `Transferencia ${result.picking_name} creada: `
                    + `${this.formatQty(result.qty_to_order)} uds. de "${result.product_name}".`,
                    { type: 'success', sticky: false },
                );
            } else {
                this.notification.add(result.message || 'Error al crear la transferencia.', {
                    type: 'warning',
                    sticky: false,
                });
            }
        } catch (error) {
            this.notification.add(
                `Error inesperado al solicitar reabastecimiento de "${display_name}".`,
                { type: 'danger', sticky: false },
            );
            console.error('[bi_pos_stock] requestRestockReplenishment error:', error);
        } finally {
            const next = new Set(this.state.requestingRestock);
            next.delete(orderpoint_id);
            this.state.requestingRestock = next;
        }
    }
}

registry.category("pos_pages").add("StockScreen", {
    name: "StockScreen",
    component: StockScreen,
    route: `/pos/ui/${odoo.pos_config_id}/stock`,
    params: {},
});
