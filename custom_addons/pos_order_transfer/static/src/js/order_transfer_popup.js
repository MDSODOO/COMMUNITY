/** @odoo-module */

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * OrderTransferPopup
 *
 * Popup que muestra la lista de empleados disponibles para recibir
 * la cesión de un pedido en curso. El componente Dialog de @web/core
 * se encarga del backdrop, animación y cierre con Escape/click-fuera.
 *
 * Props (inyectados por this.dialog.add()):
 *   - employees : Array<hr.employee>  — empleados destino (sin el actual)
 *   - onSelect  : Function(employee)  — callback al elegir un empleado
 *   - close     : Function            — inyectado automáticamente por el dialog service
 */
export class OrderTransferPopup extends Component {
    static template = "pos_order_transfer.OrderTransferPopup";
    static components = { Dialog };
    static props = {
        employees: { type: Array },
        onSelect: { type: Function },
        close: { type: Function },
    };

    /**
     * Al seleccionar un empleado, se ejecuta el callback y se cierra el popup.
     * @param {Object} employee — registro reactivo de hr.employee
     */
    selectEmployee(employee) {
        this.props.onSelect(employee);
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
