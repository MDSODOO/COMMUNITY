/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";

/**
 * Tras el RPC de actualización del catálogo, refresca el record desde el
 * backend para que la card muestre la cantidad realmente persistida (puede
 * haber sido clampeada). El dialog informativo lo dispara el backend vía
 * bus.bus → clamp_dialog_service.js.
 */
patch(ProductCatalogKanbanController.prototype, {
    async updateQuantity(record, quantity) {
        const result = await super.updateQuantity(record, quantity);
        try {
            if (record && typeof record.load === "function") {
                await record.load();
            } else if (this.model && typeof this.model.load === "function") {
                await this.model.load();
            }
        } catch (_e) {
            // No bloquear la UI si el refresh falla.
        }
        return result;
    },
});
