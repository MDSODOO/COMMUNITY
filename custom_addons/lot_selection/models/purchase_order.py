import logging
from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_confirm(self):
        # Sync final OC→lote (por si el write previo no disparó, p.ej. en
        # flujos RPC donde no se toca lot_expiration_date explícitamente).
        for order in self:
            order.order_line._sync_lot_expiration_to_stock_lot()

        # Validación bloqueante: detiene la confirmación si algún lote
        # queda con fecha ausente o vencida. Evita que la recepción o
        # una entrega posterior dispare "productos caducados".
        self._validate_lot_expiration_dates()

        res = super().action_confirm()

        pickings = self.env['stock.picking'].search([
            ('purchase_id', 'in', self.ids),
            ('state', 'not in', ('done', 'cancel')),
        ])
        if pickings:
            pickings._propagar_lotes_de_compra()

        return res

    def _validate_lot_expiration_dates(self):
        now = fields.Datetime.now()
        problemas = []
        for order in self:
            for line in order.order_line:
                lot = line.lot_id
                if not lot:
                    continue
                if not getattr(lot.product_id, 'use_expiration_date', False):
                    continue
                fecha = line.lot_expiration_date or lot.expiration_date
                if not fecha:
                    problemas.append(
                        "  • Producto '%s', lote '%s': sin fecha de caducidad." % (
                            line.product_id.display_name, lot.name,
                        )
                    )
                elif fecha < now:
                    problemas.append(
                        "  • Producto '%s', lote '%s': fecha %s ya vencida." % (
                            line.product_id.display_name, lot.name,
                            fields.Datetime.to_string(fecha),
                        )
                    )
        if problemas:
            raise UserError(_(
                "No es posible confirmar la compra. Corrija estas fechas de "
                "caducidad en la columna 'Caduca' de la línea:\n\n%s\n\n"
                "Sugerencia: use la opción 'Crear y editar...' al crear el "
                "lote para ingresar la fecha en el formulario completo."
            ) % "\n".join(problemas))
