# -*- coding: utf-8 -*-
from odoo import fields, models


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
