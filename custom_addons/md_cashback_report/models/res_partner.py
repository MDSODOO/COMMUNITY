# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_cashback_split_scheme = fields.Boolean(
        string='Esquema descuento 2% + cashback 5%',
        default=False,
        help=(
            'Cliente con esquema de descuento global del 7%: 2% aplicado '
            'directamente por línea en cada factura y 5% acumulado como '
            'provisión de devolución en efectivo (cashback) a fin de mes. '
            'Al activarlo, este cliente aparece en el reporte de '
            'trazabilidad de cashback en cuanto se capture el 2% de '
            'descuento en sus facturas.'
        ),
    )
    x_cashback_excluded_product_ids = fields.Many2many(
        'product.product',
        'res_partner_cashback_excluded_product_rel',
        'partner_id', 'product_id',
        string='Productos Excluidos de Cashback',
        help=(
            'Productos que, aunque aparezcan en facturas de este cliente, '
            'no son elegibles para el esquema de descuento 2% + cashback '
            '5% (p. ej. por acuerdo comercial o restricción de categoría). '
            'Sus líneas se excluyen del Monto Base, del Descuento Aplicado '
            'y de la Provisión/Cashback Real en el reporte de trazabilidad, '
            'y no se marcan como anomalía aunque no lleven el 2% de '
            'descuento.'
        ),
    )
    x_cashback_excluded_count = fields.Integer(
        string='Cantidad de Productos Excluidos de Cashback',
        compute='_compute_cashback_excluded_count',
    )

    @api.depends('x_cashback_excluded_product_ids')
    def _compute_cashback_excluded_count(self):
        # active_test=False: la exclusión debe contar aunque el producto esté
        # archivado -- las vistas SQL de cashback ya la respetan sin filtrar
        # por active, así que el contador y el popup deben coincidir con eso.
        for partner in self:
            partner.x_cashback_excluded_count = len(
                partner.with_context(active_test=False).x_cashback_excluded_product_ids
            )

    def action_view_cashback_excluded_products(self):
        self.ensure_one()
        return {
            'name': _('Productos Excluidos de Cashback'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(
                self.env.ref('md_cashback_report.view_partner_form_cashback_excluded_popup').id,
                'form',
            )],
            'target': 'new',
            'context': {'active_test': False},
        }
