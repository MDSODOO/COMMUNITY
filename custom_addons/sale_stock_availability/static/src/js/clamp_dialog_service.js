/** @odoo-module **/
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

/**
 * Servicio que escucha bus.bus para mostrar un dialog cuando el backend
 * clampea cantidad por exceder stock del warehouse. Se dispara desde
 * sale.order._notify_stock_clamped() vía bus._sendone().
 *
 * Funciona globalmente: catálogo, edición de líneas, importaciones,
 * cualquier path que llame al backend.
 */
const saleStockClampDialogService = {
    dependencies: ["bus_service", "dialog"],
    start(env, { bus_service, dialog }) {
        bus_service.subscribe("sale_stock_availability/clamp_dialog", (payload) => {
            if (!payload) return;
            dialog.add(AlertDialog, {
                title: payload.title || _t("Cantidad ajustada"),
                body: payload.message || "",
                confirmLabel: _t("Cerrar"),
            });
        });
        bus_service.start();
    },
};

registry.category("services").add(
    "sale_stock_availability_clamp_dialog",
    saleStockClampDialogService,
);
