# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from .margin_tools import get_standard_cost_for_line

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qfm_margin_pct = fields.Float(
        string='Margen Compra (%)',
        compute='_compute_qfm_purchase_margin',
        store=False,
        readonly=True,
        digits=(16, 2),
        help=(
            'Diferencial vs. costo estandar del producto: '
            '(costo_estandar - precio_compra) / precio_compra * 100. '
            'No representa un margen comercial de venta. '
            'Positivo cuando se compra por debajo del costo estandar (ahorro); '
            'negativo cuando se compra por encima (sobreprecio).'
        ),
    )

    qfm_margin_abs = fields.Float(
        string='Margen Compra (Importe)',
        compute='_compute_qfm_purchase_margin',
        store=False,
        readonly=True,
        digits=(16, 2),
        help=(
            'Importe del diferencial vs. costo estandar: '
            '(costo_estandar - precio_compra) * cantidad.'
        ),
    )

    @api.depends(
        'price_unit',
        'product_id',
        'product_id.standard_price',
        'product_uom_id',
        'product_qty',
        'order_id.currency_id',
        'order_id.company_id',
        'order_id.date_order',
    )
    def _compute_qfm_purchase_margin(self):
        for line in self:
            line.qfm_margin_pct = 0.0
            line.qfm_margin_abs = 0.0
            try:
                costo_estandar = get_standard_cost_for_line(line, 'product_uom_id')
                precio_compra = line.price_unit or 0.0
                cantidad = line.product_qty or 0.0
                margen_unitario = costo_estandar - precio_compra

                if precio_compra > 0:
                    line.qfm_margin_pct = margen_unitario / precio_compra * 100.0
                line.qfm_margin_abs = margen_unitario * cantidad
            except (UserError, ValidationError):
                raise
            except Exception:
                _logger.exception(
                    'QFM margins: no se pudo calcular margen de compra para linea %s',
                    line.id or 'new',
                )

    @api.onchange('product_id', 'price_unit', 'product_uom_id', 'product_qty')
    def _onchange_qfm_purchase_margin_warning(self):
        if self.product_id and self.price_unit:
            try:
                costo = get_standard_cost_for_line(self, 'product_uom_id')
            except (UserError, ValidationError):
                raise
            except Exception:
                _logger.exception(
                    'QFM margins: no se pudo evaluar alerta de compra para linea %s',
                    self.id or 'new',
                )
                return
            if self.price_unit > costo:
                return {
                    'warning': {
                        'title': 'Precio de Compra Superior al Costo Estándar',
                        'message': (
                            f'El precio de compra (${self.price_unit:.2f}) es MAYOR '
                            f'al costo estándar (${costo:.2f}).\n\n'
                            f'Esto generará un margen NEGATIVO en esta línea.'
                        ),
                    }
                }
