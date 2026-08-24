# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    qfm_target_margin_pct = fields.Float(
        string='Margen Objetivo (%)',
        digits=(5, 2),
        default=0.0,
        help=(
            'Porcentaje de margen sobre precio de venta deseado para este producto. '
            'Se usa para sugerir un precio de venta sin cambiarlo automaticamente.'
        ),
    )

    qfm_suggested_list_price = fields.Float(
        string='Precio de Venta Sugerido',
        compute='_compute_qfm_suggested_list_price',
        store=False,
        readonly=True,
        digits=(16, 2),
        help=(
            'Precio de venta sugerido con base en el costo estándar y el margen '
            'objetivo configurado. No se aplica automaticamente.'
        ),
    )

    cost_history_ids = fields.One2many(
        'product.cost.history',
        'product_tmpl_id',
        string='Historial de costos de compra',
        readonly=True,
    )

    @api.constrains('qfm_target_margin_pct')
    def _check_qfm_target_margin_pct(self):
        for tmpl in self:
            margin = tmpl.qfm_target_margin_pct or 0.0
            if margin < 0.0 or margin >= 100.0:
                raise ValidationError(_(
                    'El margen objetivo del producto debe estar entre 0 y 99.99%.'
                ))

    @api.depends('standard_price', 'qfm_target_margin_pct')
    def _compute_qfm_suggested_list_price(self):
        for tmpl in self:
            tmpl.qfm_suggested_list_price = 0.0
            margin = tmpl.qfm_target_margin_pct or 0.0
            standard_price = tmpl.standard_price or 0.0
            if standard_price > 0 and 0 < margin < 100:
                tmpl.qfm_suggested_list_price = standard_price / (1 - margin / 100.0)

    def action_apply_suggested_price(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Actualización de precio deshabilitada'),
                'message': _(
                    'La actualización automática del precio de venta por margen '
                    'ya no está activa.'
                ),
                'type': 'warning',
                'sticky': False,
            },
        }
