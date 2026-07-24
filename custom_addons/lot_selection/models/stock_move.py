import logging
from odoo import models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        self.ensure_one()
        vals = super()._prepare_move_line_vals(
            quantity=quantity, reserved_quant=reserved_quant
        )

        if self.product_id.tracking == 'none':
            return vals

        pol = self.purchase_line_id
        if not pol or not pol.lot_id:
            return vals

        lot = pol.lot_id
        if lot.product_id != self.product_id:
            return vals
        if lot.company_id and lot.company_id != self.company_id:
            return vals

        vals['lot_id'] = lot.id
        return vals
