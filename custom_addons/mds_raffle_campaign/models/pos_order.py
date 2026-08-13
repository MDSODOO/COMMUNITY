from odoo import api, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _process_order(self, order, existing_order):
        # Firma real en Odoo 19 (core/pos_order.py): _process_order(self,
        # order, existing_order) -> devuelve un id (int), no un recordset.
        order_id = super()._process_order(order, existing_order)
        pos_order = self.browse(order_id)
        if pos_order.state == 'paid':
            self.env['raffle.campaign']._evaluate_order_for_tickets(pos_order)
        return order_id
