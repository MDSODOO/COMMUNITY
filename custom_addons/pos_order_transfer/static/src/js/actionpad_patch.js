/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { OrderTransferPopup } from "@pos_order_transfer/js/order_transfer_popup";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch al componente Actionpad del POS.
 *
 * Metodología:  Odoo 19 usa `patch()` de @web/core/utils/patch para extender
 * componentes OWL 2 sin modificar el código fuente. El patch se aplica al
 * *prototype* del componente, lo que permite:
 *   - Llamar super.setup() para preservar la inicialización original.
 *   - Inyectar servicios adicionales (dialog, notification) vía hooks de OWL.
 *   - Agregar métodos nuevos que quedan disponibles en la template extendida.
 *
 * IMPORTANTE sobre hooks en patches:
 *   Los hooks de OWL (useService, useState, etc.) SOLO se pueden llamar dentro
 *   de setup(). Por eso inyectamos `dialog` y `notification` aquí, aunque el
 *   Actionpad original ya pudiera tener alguno. useService() retorna la misma
 *   instancia del servicio si ya fue registrada, así que es seguro.
 */
patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);
        // Inyectar servicios necesarios para el popup y las notificaciones.
        // Si el Actionpad original ya los tiene, useService retorna la misma ref.
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },

    /**
     * Propiedad computada para controlar la visibilidad del botón en la template.
     * Solo muestra el botón si el POS tiene habilitado el inicio de sesión con
     * empleados (module_pos_hr en la configuración del POS).
     */
    get canTransferOrder() {
        return this.pos.config.module_pos_hr;
    },

    /**
     * Flujo principal de la cesión de pedido:
     *
     * 1. Validaciones previas (pedido existente, con líneas, empleados disponibles).
     * 2. Abrir popup con la lista de empleados (excluyendo al cajero actual).
     * 3. Al seleccionar destino:
     *    a. Reasignar employee_id en el pedido (asignación directa sobre el
     *       modelo reactivo — OWL 2 detecta el cambio automáticamente).
     *    b. Crear un nuevo pedido vacío para el cajero actual (add_new_order()
     *       lo crea con employee_id = cajero actual automáticamente).
     *    c. Notificar éxito.
     *
     * Resultado: el pedido transferido queda asociado al empleado destino.
     * Cuando ese empleado inicie sesión con su PIN/gafete, el POS filtra los
     * pedidos por employee_id y le mostrará el pedido cedido.
     */
    transferOrder() {
        const order = this.pos.getOrder();

        // — Validación: pedido vacío
        if (!order || !order.lines || order.lines.length === 0) {
            this.notification.add(
                "El pedido actual está vacío. Agrega productos antes de cederlo.",
                { type: "warning" }
            );
            return;
        }

        // — Obtener cajero actual y lista de empleados
        const currentCashier = this.pos.cashier;
        const allEmployees = this.pos.models["hr.employee"].getAll();

        // Filtrar al empleado activo para no mostrarlo en la lista
        const availableEmployees = allEmployees.filter(
            (emp) => emp.id !== currentCashier?.id
        );

        if (availableEmployees.length === 0) {
            this.notification.add(
                "No hay otros empleados registrados en este POS.",
                { type: "warning" }
            );
            return;
        }

        // — Abrir popup de selección
        this.dialog.add(OrderTransferPopup, {
            employees: availableEmployees,
            onSelect: (selectedEmployee) => {
                // Reasignación directa: el modelo reactivo de OWL 2 propaga
                // el cambio a todos los componentes que observen este campo.
                order.employee_id = selectedEmployee;

                // Crear un nuevo pedido vacío para el cajero actual.
                // add_new_order() usa internamente get_cashier() para asignar
                // el employee_id del nuevo pedido, y lo selecciona como activo.
                this.pos.addNewOrder();

                this.notification.add(
                    `Pedido cedido a ${selectedEmployee.name} exitosamente.`,
                    { type: "success" }
                );
            },
        });
    },
});
