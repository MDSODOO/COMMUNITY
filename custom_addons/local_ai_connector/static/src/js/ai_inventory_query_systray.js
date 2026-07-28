/** @odoo-module **/
/**
 * Icono en el systray del backend que abre el copiloto de inventario en
 * lenguaje natural (AiInventoryQueryDialog). Mismo patron que el toggle de
 * custom_addons/md_dark_mode (componente OWL registrado en systray).
 *
 * El acceso via Ctrl+K vive en ./launcher_quick_actions.js (registry
 * "md_launcher_quick_actions"), no aqui -- este archivo antes usaba
 * useCommand() para eso, pero se descubrio en auditoria (2026-07-28) que
 * el Command Palette nativo de Odoo (del que depende useCommand) nunca se
 * abre en esta instancia: md_command_palette intercepta Ctrl+K/Alt+Espacio
 * en fase de captura con stopImmediatePropagation() antes de que el
 * hotkey service nativo lo reciba. La entrada "Copiloto de inventario"
 * jamas aparecio en la paleta real pese a lo que decia el commit 80e3573.
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
