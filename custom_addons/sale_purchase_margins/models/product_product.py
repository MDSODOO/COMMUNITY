from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_apply_suggested_price(self):
        """Delegate to the disabled template-level legacy action.

        In Odoo 19, product form inheritance chains (including website_sale) can
        validate object buttons against product.product. Keeping this bridge
        method avoids view validation errors.
        """
        templates = self.mapped('product_tmpl_id')
        templates.action_apply_suggested_price()
        return True
