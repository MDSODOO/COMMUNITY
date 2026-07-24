from odoo import api, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @staticmethod
    def _md_m2o_id(value):
        if hasattr(value, 'id'):
            return value.id
        if isinstance(value, (list, tuple)):
            return value[0] if value else False
        return value

    def _md_assign_existing_global_lot_vals(self, vals):
        vals = dict(vals)
        if vals.get('lot_id') or not vals.get('lot_name'):
            return vals

        lot_name = (vals.get('lot_name') or '').strip()
        product_id = self._md_m2o_id(vals.get('product_id'))
        if not product_id and len(self) == 1:
            product_id = self.product_id.id
        if not lot_name or not product_id:
            return vals
        vals['lot_name'] = lot_name

        product = self.env['product.product'].browse(product_id).exists()
        if not product:
            return vals

        lot = self.env['stock.lot']._md_find_existing_lot(lot_name, product.id, False)
        if lot:
            vals['lot_id'] = lot.id
            vals['lot_name'] = lot.name
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [
            self._md_assign_existing_global_lot_vals(vals)
            for vals in vals_list
        ]
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('lot_name') and not vals.get('lot_id') and len(self) > 1:
            result = True
            for line in self:
                result = (
                    super(StockMoveLine, line).write(
                        line._md_assign_existing_global_lot_vals(vals)
                    )
                    and result
                )
            return result

        vals = self._md_assign_existing_global_lot_vals(vals)
        return super().write(vals)
