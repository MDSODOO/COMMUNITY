/** @odoo-module **/
/**
 * Icono en el systray del backend que abre el copiloto de inventario en
 * lenguaje natural (AiInventoryQueryDialog). Mismo patron que el toggle de
 * custom_addons/md_dark_mode (componente OWL registrado en systray).
 *
 * Tambien se registra como comando fijo del Command Palette (Ctrl+K) via
 * useCommand -- NO se implemento como command_provider con busqueda en
 * vivo (options.searchValue) porque una consulta real tarda 10-25s+ y el
 * Command Palette esta pensado para resultados casi instantaneos; forzar
 * eso ahi se hubiera sentido "congelado", no una mejora. En vez de eso, el
 * comando simplemente abre el mismo dialogo ya probado -- Ctrl+K como
 * atajo de descubrimiento, no como buscador en vivo.
 */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useCommand } from "@web/core/commands/command_hook";
import { AiInventoryQueryDialog } from "./ai_inventory_query_dialog";

export class AiInventoryQuerySystrayIcon extends Component {
    static template = "local_ai_connector.SystrayIcon";
    static props = {};

    setup() {
        this.dialog = useService("dialog");
        useCommand("Copiloto de inventario (IA local)", () => this.openDialog(), {
            category: "default",
        });
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
