from odoo import models, fields


class SaleRestrictedSku(models.Model):
    _name = 'sale.restricted.sku'
    _description = 'Restricted Product SKU (EAN)'
    _order = 'ean'

    ean = fields.Char(
        string='EAN Code',
        required=True,
        index=True,
        help='Barcode/EAN of restricted product',
    )
    marca = fields.Char(string='Brand')
    nombre = fields.Char(string='Product Name')
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        help='Link to product if found in catalog',
    )

    _ean_uniq = models.Constraint(
        'UNIQUE(ean)',
        'EAN code must be unique.',
    )

    def name_get(self):
        return [(r.id, f"{r.ean} - {r.marca}") for r in self]
