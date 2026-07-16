# -*- coding: utf-8 -*-
from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_md_similar_products(self, limit=12):
        # qty_available is computed (not stored), so filter in Python after search.
        candidates = self.env['product.template'].sudo().search([
            ('id', '!=', self.id),
            ('categ_id', '=', self.categ_id.id),
            ('website_published', '=', True),
            ('sale_ok', '=', True),
        ], limit=limit * 4)
        return candidates.filtered(
            lambda p: p.type != 'product' or p.qty_a_la_mano > 0
        )[:limit]
