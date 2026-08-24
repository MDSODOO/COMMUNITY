# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    qfm_receipt_price_update_policy = fields.Selection(
        selection=[
            ('always_update', 'Siempre actualizar precio'),
            ('only_increase', 'Solo aumentar precio'),
            ('manual_review', 'Solo sugerir (sin actualizar)'),
        ],
        string='Política de precio por recepción',
        default='always_update',
        help=(
            'Define cómo actualizar list_price al validar recepciones de compra: '
            '"Siempre actualizar", "Solo aumentar" o "Solo sugerir".'
        ),
    )
