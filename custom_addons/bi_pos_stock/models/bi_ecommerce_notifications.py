# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """Send a real-time bus.bus notification to the matching POS session
    whenever a website (e-commerce) sale order is confirmed.

    Only active when the 'website_sale' module is installed (checked at
    runtime via field introspection — no hard dependency required).
    """
    _inherit = 'sale.order'

    def action_confirm(self):
        result = super().action_confirm()
        self._notify_pos_ecommerce_branch()
        return result

    def _notify_pos_ecommerce_branch(self):
        """Push an ECOMMERCE_ORDER message to every open POS session
        whose warehouse matches the confirmed order's warehouse.

        Channel naming mirrors the existing BRANCH_STOCK_UPDATED pattern:
            'pos_config_{config_id}'
        so the frontend only needs one subscription per config.
        """
        # Graceful degradation: skip silently if website_sale is not installed.
        if 'website_id' not in self._fields:
            return

        for order in self:
            if not order.website_id:
                # Not an e-commerce order — nothing to do.
                continue

            warehouse = order.warehouse_id
            if not warehouse:
                continue

            # Find POS configs whose picking type uses the same warehouse.
            pos_configs = self.env['pos.config'].search([
                ('picking_type_id.warehouse_id', '=', warehouse.id),
            ])

            for config in pos_configs:
                # Only notify sessions that are currently open.
                if config.current_session_state != 'opened':
                    continue

                channel = f'pos_config_{config.id}'
                payload = {
                    'order_id': order.id,
                    'order_name': order.name,
                    'partner_name': order.partner_id.name or _('Cliente desconocido'),
                    'amount_total': order.amount_total,
                    'currency_symbol': order.currency_id.symbol or '$',
                    'product_count': len(order.order_line),
                }

                try:
                    self.env['bus.bus']._sendone(channel, 'ECOMMERCE_ORDER', payload)
                    _logger.info(
                        "[bi_pos_stock] ECOMMERCE_ORDER sent → channel '%s' (order '%s').",
                        channel, order.name,
                    )
                except Exception as exc:  # noqa: BLE001
                    _logger.warning(
                        "[bi_pos_stock] Failed to send ECOMMERCE_ORDER for '%s': %s",
                        order.name, exc,
                    )
