# -*- coding: utf-8 -*-
# Part of Medicine Depot. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    rectification_log_ids = fields.One2many(
        'pos.payment.rectification.log', 'order_id', string='Rectificaciones de pago',
    )
    rectification_count = fields.Integer(
        string='Rectificaciones', compute='_compute_rectification_count',
    )

    def _compute_rectification_count(self):
        counts = self.env['pos.payment.rectification.log']._read_group(
            [('order_id', 'in', self.ids)], ['order_id'], ['__count'],
        )
        count_by_order = {order.id: count for order, count in counts}
        for order in self:
            order.rectification_count = count_by_order.get(order.id, 0)

    def action_open_payment_rectifier_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rectificar Método de Pago',
            'res_model': 'pos.payment.rectifier.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def action_view_rectification_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rectificaciones de Pago',
            'res_model': 'pos.payment.rectification.log',
            'view_mode': 'list,form',
            'domain': [('order_id', '=', self.id)],
        }
