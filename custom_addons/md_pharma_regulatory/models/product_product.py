# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    cofepris_full_name = fields.Char(
        string='Nombre Completo COFEPRIS (NOM-072)',
        related='product_tmpl_id.cofepris_full_name',
        readonly=True,
    )

    def _get_cofepris_full_name(self):
        """Devuelve el nombre concatenado de COFEPRIS según la norma NOM-072-SSA1-2012."""
        self.ensure_one()
        return self.product_tmpl_id._get_cofepris_full_name()
