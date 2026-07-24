/** @odoo-module */
/**
 * Widget de campo — botón dedicado que abre MdKanbanLotDetailPopup desde la
 * card del Kanban de Inventario > Productos. Se enlaza al campo "id"
 * (solo-lectura, ya disponible en todo registro) porque el widget no
 * renderiza ningún valor de campo — solo usa record.resId/record.data.name
 * para la llamada RPC. Mismo patrón que cualquier "botón de acción" custom
 * en un kanban: un widget con acceso a useService, algo que un <a type="object">
 * de solo XML no puede dar (esos llaman métodos server-side que devuelven
 * ir.actions.act_window, no abren un componente OWL directamente).
 */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { MdKanbanLotDetailPopup } from "./kanban_lot_detail_popup";

export class MdLotDetailButton extends Component {
    static template = "md_pharma_regulatory.MdLotDetailButton";
    static props = { ...standardFieldProps };

    setup() {
        this.dialog = useService("dialog");
    }

    openPopup(ev) {
        ev.stopPropagation(); // no abrir el registro completo al hacer clic
        this.dialog.add(MdKanbanLotDetailPopup, {
            productId: this.props.record.resId,
            productName: this.props.record.data.name,
        });
    }
}

export const mdLotDetailButton = {
    component: MdLotDetailButton,
    displayName: "Botón detalle de lotes FEFO",
    supportedTypes: ["integer"],
};

registry.category("fields").add("md_lot_detail_button", mdLotDetailButton);
