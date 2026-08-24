# -*- coding: utf-8 -*-
# Part of Medicine Depot. See LICENSE file for full copyright and licensing details.

"""
Rastro de auditoría permanente para rectificaciones de método de pago PoS.

Deliberadamente NO es un TransientModel: es el registro legal de que un
gerente movió dinero de una cuenta puente (ej. Tarjeta) a otra (ej. Efectivo)
para una orden específica, y por qué. No se expone ninguna acción de
escritura/borrado desde la UI (ver ir.model.access.csv) — solo se crea desde
``pos.payment.rectifier.wizard`` vía ``sudo()``.
"""

from odoo import fields, models


class PosPaymentRectificationLog(models.Model):
    _name = 'pos.payment.rectification.log'
    _description = 'Rectificación de Método de Pago PoS — Log de Auditoría'
    _order = 'create_date desc'

    order_id = fields.Many2one(
        'pos.order', string='Orden PoS', required=True, readonly=True, ondelete='restrict',
    )
    session_id = fields.Many2one(
        related='order_id.session_id', string='Sesión', store=True, readonly=True,
    )
    old_payment_method_id = fields.Many2one(
        'pos.payment.method', string='Método original (erróneo)', required=True, readonly=True,
    )
    new_payment_method_id = fields.Many2one(
        'pos.payment.method', string='Método corregido', required=True, readonly=True,
    )
    amount = fields.Monetary(string='Monto', required=True, readonly=True)
    currency_id = fields.Many2one(
        related='order_id.currency_id', string='Moneda', store=True, readonly=True,
    )
    reason = fields.Text(string='Motivo', required=True, readonly=True)
    reclass_move_id = fields.Many2one(
        'account.move', string='Asiento de reclasificación', readonly=True, ondelete='restrict',
    )
    state = fields.Selection([
        ('done', 'Completado'),
        ('needs_review', 'Requiere revisión manual'),
    ], string='Estado', required=True, readonly=True, default='done')
    review_note = fields.Text(string='Nota de revisión', readonly=True)
