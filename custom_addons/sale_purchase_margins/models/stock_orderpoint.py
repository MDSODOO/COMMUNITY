# -*- coding: utf-8 -*-
import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class StockOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    def action_qfm_update_price_from_replenishment(self):
        """Legacy server action kept as a disabled no-op."""
        _logger.info(
            'QFM margins: acción de actualización de precio por margen '
            'deshabilitada en reabastecimiento.'
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Actualización de precios por margen deshabilitada'),
                'message': _(
                    'La actualización automática del precio de venta por margen '
                    'ya no está activa.'
                ),
                'type': 'warning',
                'sticky': False,
            },
        }
