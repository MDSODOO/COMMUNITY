/** @odoo-module **/
/**
 * Registra acciones rápidas para "Correo" y "Farmacovigilancia" en el Command Palette.
 */

import { registry } from "@web/core/registry";

const quickActions = registry.category("md_launcher_quick_actions");

quickActions.add("md_command_palette.mail_client", {
    id: "md_command_palette.mail_client",
    label: "Correo (Cliente de Email)",
    keywords: ["correo", "email", "mail", "bandeja", "mensajes", "enviar"],
    icon: "fa-envelope",
    run: (env) => {
        env.services.action.doAction({
            type: "ir.actions.act_window",
            name: "Correo",
            res_model: "mail.message",
            views: [[false, "list"]],
            target: "current",
        });
    },
});

quickActions.add("md_command_palette.pharmacovigilance", {
    id: "md_command_palette.pharmacovigilance",
    label: "Farmacovigilancia (Seguridad Médica)",
    keywords: ["farmacovigilancia", "seguridad", "reporte", "medicamento", "alerta", "salud", "reacciones"],
    icon: "fa-shield",
    run: (env) => {
        env.services.action.doAction({
            type: "ir.actions.act_window",
            name: "Farmacovigilancia",
            res_model: "md.pharmacovigilance",
            views: [[false, "list"]],
            target: "current",
        });
    },
});

quickActions.add("md_command_palette.purchase_xml_import", {
    id: "md_command_palette.purchase_xml_import",
    label: "Orden de Compra XML",
    keywords: ["compra", "purchase", "orden", "xml", "cfdi", "importar", "proveedor", "factura"],
    icon: "fa-file-code-o",
    run: (env) => {
        // Reutiliza la accion real del wizard de purchase_invoice_parser
        // (purchase_invoice_parser.action_cfdi_import_wizard, ir.actions.act_window
        // sobre purchase.invoice.import.wizard, target=new) via su external ID --
        // se resuelve por RPC en tiempo de ejecucion, sin declarar dependencia de
        // modulo (mismo desacoplamiento que el resto de este registry).
        env.services.action.doAction("purchase_invoice_parser.action_cfdi_import_wizard");
    },
});
