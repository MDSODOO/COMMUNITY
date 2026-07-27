/** @odoo-module **/
/**
 * Icono en el systray del backend que abre el copiloto de inventario en
 * lenguaje natural (AiInventoryQueryDialog). Mismo patron que el toggle de
 * custom_addons/md_dark_mode (componente OWL registrado en systray).
 */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { AiInventoryQueryDialog } from "./ai_inventory_query_dialog";

export class AiInventoryQuerySystrayIcon extends Component {
    static template = "local_ai_connector.SystrayIcon";
    static props = {};

    setup() {
        this.dialog = useService("dialog");
    }

    openDialog() {
        this.dialog.add(AiInventoryQueryDialog, {});
    }
}

registry.category("systray").add(
    "local_ai_connector.inventory_query",
    { Component: AiInventoryQuerySystrayIcon },
    { sequence: 2 } // junto al toggle de dark mode (sequence: 1)
);
