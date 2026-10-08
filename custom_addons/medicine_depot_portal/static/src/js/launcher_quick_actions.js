/** @odoo-module **/
/**
 * Registra acciones rápidas de medicine_depot_portal en el Command Palette
 * custom del proyecto (registry "md_launcher_quick_actions", ver
 * md_command_palette/static/src/js/launcher.js).
 */

import { registry } from "@web/core/registry";

const quickActions = registry.category("md_launcher_quick_actions");

quickActions.add("medicine_depot_portal.pharmacovigilance", {
    id: "medicine_depot_portal.pharmacovigilance",
    label: "Farmacovigilancia — Nuevo reporte",
    keywords: ["farmaco", "farmacovigilancia", "reporte", "evento", "adverso", "medicamento", "seguridad", "pharma"],
    icon: "fa-heartbeat",
    run: (env) => {
        const xmlId = "medicine_depot_portal.action_medicine_depot_pharmacovigilance_report";
        return env.services.action.doAction(xmlId);
    },
});
