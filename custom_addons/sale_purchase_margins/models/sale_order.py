# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _qfm_update_prices_on_confirm(self):
        """Legacy entry point kept as a no-op.

        Automatic sale price updates from target margin are disabled.
        """
        _logger.info(
            'QFM margins: actualización automática de precio de venta '
            'deshabilitada al confirmar pedidos.'
        )
        return True
