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
