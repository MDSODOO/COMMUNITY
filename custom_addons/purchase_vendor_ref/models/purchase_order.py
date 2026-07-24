# -*- coding: utf-8 -*-
from odoo import models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # -------------------------------------------------------------------------
    # Propagación de referencia de proveedor → factura de proveedor
    # -------------------------------------------------------------------------
    # Odoo estándar NO propaga partner_ref al crear la factura desde una OC.
    # Este módulo sobrecarga _prepare_invoice (single-PO) y _create_invoices
    # (multi-PO) para rellenar automáticamente:
    #   - ref              → "Referencia de Factura" en el formulario de factura
    #   - payment_reference → "Referencia de Pago" para conciliación bancaria
    #
    # DISEÑO ANTI-BUCLE:
    #   La propagación ocurre SOLO en la creación (write dentro de _create_invoices
    #   y asignación de vals en _prepare_invoice). No existe compute ni onchange
    #   en account.move que lea de regreso purchase.order, por lo que editar
    #   manualmente ref o payment_reference en la factura es completamente seguro.
    # -------------------------------------------------------------------------

    def _prepare_invoice(self):
        """Añade partner_ref de la OC a los valores de la factura de proveedor.

        Llamado una vez por OC durante la creación de la factura.
        El valor se propaga a ref y payment_reference. Si el campo está vacío
        en la OC, el comportamiento estándar de Odoo no se altera.
        """
        vals = super()._prepare_invoice()
        if self.partner_ref:
            vals['ref'] = self.partner_ref
            vals['payment_reference'] = self.partner_ref
        return vals

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Consolida referencias cuando varias OCs se agrupan en una sola factura.

        Escenario: el usuario selecciona N órdenes de compra con distintos
        partner_ref y hace clic en "Crear Factura". Odoo genera una sola
        account.move por grupo (mismo proveedor/moneda). En ese caso,
        _prepare_invoice() solo aporta el ref de la primera OC del grupo;
        las demás se pierden.

        Este override detecta facturas generadas desde más de una OC y
        reconstruye ref / payment_reference como:
            "REF-001 / REF-002 / REF-003"
        conservando el orden de inserción y eliminando duplicados.

        Facturas de una sola OC no se modifican: el ref de _prepare_invoice ya
        es correcto y este bloque no escribe nada.
        """
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)

        for invoice in invoices.filtered(lambda m: m.move_type == 'in_invoice'):
            # Recorre las líneas de la factura para recuperar las OCs origen.
            # purchase_line_id es el campo estándar de Odoo en account.move.line
            # que enlaza cada línea con su purchase.order.line.
            purchase_orders = invoice.line_ids.mapped('purchase_line_id.order_id')

            # dict.fromkeys preserva orden de primera aparición y elimina duplicados.
            refs = list(dict.fromkeys(
                po.partner_ref for po in purchase_orders if po.partner_ref
            ))

            if len(refs) > 1:
                combined = ' / '.join(refs)
                # write() en lugar de asignación directa para respetar el ORM
                # (computed inverses, tracking, etc.) sin disparar onchanges de UI.
                invoice.write({
                    'ref': combined,
                    'payment_reference': combined,
                })

        return invoices
