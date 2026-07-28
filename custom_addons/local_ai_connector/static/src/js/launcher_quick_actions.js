/** @odoo-module **/
/**
 * Registra las "acciones rapidas" de este modulo en el Command Palette
 * custom del proyecto (registry "md_launcher_quick_actions", ver
 * md_command_palette/static/src/js/launcher.js). Modulo productor: no
 * depende de md_command_palette ni viceversa (mismo desacoplamiento que ya
 * usan los registries nativos de Odoo) -- si md_command_palette no esta
 * instalado, estas entradas simplemente no se leen en ningun lado.
 *
 * "run(env)" recibe el Env de OWL del propio launcher y abre el dialogo
 * via env.services.dialog -- no necesita un componente montado propio para
 * poder dispararse desde la paleta.
 */

import { registry } from "@web/core/registry";
import { AiInventoryQueryDialog } from "./ai_inventory_query_dialog";
import { ImageQuoteDropDialog } from "./image_quote_drop_dialog";

const quickActions = registry.category("md_launcher_quick_actions");

quickActions.add("local_ai_connector.inventory_query", {
    id: "local_ai_connector.inventory_query",
    label: "Copiloto de inventario (IA local)",
    keywords: ["inventario", "stock", "a la mano", "copiloto", "ia"],
    icon: "fa-comments-o",
    run: (env) => env.services.dialog.add(AiInventoryQueryDialog, {}),
});

quickActions.add("local_ai_connector.image_quote_drop", {
    id: "local_ai_connector.image_quote_drop",
    label: "Nueva cotización desde imagen (foto de WhatsApp)",
    keywords: ["cotizacion", "imagen", "foto", "whatsapp", "arrastrar", "ia"],
    icon: "fa-camera",
    run: (env) => env.services.dialog.add(ImageQuoteDropDialog, {}),
});
