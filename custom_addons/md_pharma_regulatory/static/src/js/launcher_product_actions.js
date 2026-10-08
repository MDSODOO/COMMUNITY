/** @odoo-module **/
/**
 * Registra los 3 accesos rápidos de la card del Kanban de Inventario >
 * Productos (COFEPRIS, detalle de lotes FEFO, Ajustar A la mano) también
 * dentro de cada fila de resultado de producto del Command Palette custom
 * (registry "md_launcher_product_actions", ver
 * md_command_palette/static/src/js/launcher.js). Modulo productor: no
 * depende de md_command_palette ni viceversa (mismo desacoplamiento que ya
 * usa local_ai_connector/static/src/js/launcher_quick_actions.js) -- si
 * md_command_palette no esta instalado, estas entradas simplemente no se
 * leen en ningun lado.
 *
 * Los 3 iconos y las 3 acciones son EXACTAMENTE los mismos que
 * views/product_visual_views.xml ya renderiza en ".md-card-top-actions"
 * (fa-flask / md_lot_detail_button widget / fa-sliders) -- no se inventa
 * ningun boton nuevo, solo se reexponen para poder dispararse sin abrir la
 * ficha completa del producto, igual que en el Kanban.
 */

import { registry } from "@web/core/registry";
import { MdKanbanLotDetailPopup } from "../kanban_lot_detail/kanban_lot_detail_popup";

const productActions = registry.category("md_launcher_product_actions");

productActions.add("md_pharma_regulatory.cofepris_detail", {
    id: "md_pharma_regulatory.cofepris_detail",
    title: "Detalle regulatorio COFEPRIS",
    icon: "fa-flask",
    // Mismo color que .md-cofepris-btn en el Kanban (product_kanban_pos_style.scss)
    colorClass: "cofepris",
    // action_open_cofepris_detail (product_template.py) devuelve un
    // ir.actions.act_window con target=new -- mismo patron que el boton
    // type="object" del Kanban, replicado via ORM + action service.
    run: async (env, record) => {
        const action = await env.services.orm.call(
            "product.template",
            "action_open_cofepris_detail",
            [[record.product_tmpl_id[0]]]
        );
        env.services.action.doAction(action);
    },
});

productActions.add("md_pharma_regulatory.lot_detail", {
    id: "md_pharma_regulatory.lot_detail",
    title: "Ver detalle de lotes (FEFO)",
    icon: "fa-list-ol",
    // Mismo color que .md-lot-detail-btn en el Kanban.
    colorClass: "lot",
    // Misma condicion que el widget md_lot_detail_button en el Kanban: solo
    // aplica a productos con tracking por lote/serie.
    visible: (record) => record.tracking === "lot" || record.tracking === "serial",
    run: (env, record) => {
        env.services.dialog.add(MdKanbanLotDetailPopup, {
            productId: record.product_tmpl_id[0],
            productName: record.display_name,
        });
    },
});

productActions.add("md_pharma_regulatory.adjust_onhand", {
    id: "md_pharma_regulatory.adjust_onhand",
    title: "Ajustar A la mano",
    icon: "fa-sliders",
    // Mismo color que .md-adjust-qty-btn en el Kanban.
    colorClass: "adjust",
    // action_open_quants (stock/models/product.py, nativo) -- mismo metodo
    // que ya dispara el boton "Ajustar A la mano" de esta misma card.
    run: async (env, record) => {
        const action = await env.services.orm.call(
            "product.template",
            "action_open_quants",
            [[record.product_tmpl_id[0]]]
        );
        env.services.action.doAction(action);
    },
});
