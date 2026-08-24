import logging

from odoo import _, api, Command, fields, models

_logger = logging.getLogger(__name__)


class PosOrderInherit(models.Model):
    _inherit = 'pos.order'

    payment_method_id = fields.Many2one("pos.payment.method", string="Metodo de pago", readonly=False,
                                        compute="_compute_payment_method", store=True)

    reverse_move = fields.Many2one('account.move', string='Reverse Move', readonly=True, copy=False)

    @api.depends('payment_method_id', 'payment_ids')
    def _compute_payment_method(self):
        for rec in self:
            if rec.payment_ids:
                payments = sorted(rec.payment_ids, key=lambda x: x.amount, reverse=True)
                rec.payment_method_id = payments[0].payment_method_id.id


    @api.depends('account_move','account_move.state')
    def _compute_invoice_status(self):
        for order in self:
            order.invoice_status = 'invoiced' if len(order.account_move.filtered(lambda x: x.state in ['posted','draft'])) else 'to_invoice'


    def _get_invoice_lines_values(self, line_values, pos_line, move_type):
        # correct quantity sign based on move type and if line is refund.
        values = super()._get_invoice_lines_values(line_values,pos_line,move_type)

        values['name'] = pos_line.product_id.display_name
        return values