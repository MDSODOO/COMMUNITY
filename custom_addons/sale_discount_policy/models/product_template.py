from odoo import models, fields, api


RESTRICTED_BRAND_PREFIX = "MARCA_RESTRINGIDA_"


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_discount_restricted = fields.Boolean(
        string='Excluded from Farmacias Discount',
        compute='_compute_is_discount_restricted',
        compute_sudo=True,
        store=True,
        help='True if product has a restricted brand or SKU for group discount.',
    )

    @api.depends('product_tag_ids.name', 'barcode', 'product_variant_ids.default_code')
    def _compute_is_discount_restricted(self):
        # Get all restricted EANs once for efficiency
        restricted_skus = self.env['sale.restricted.sku'].search([])
        restricted_eans = set(restricted_skus.mapped('ean'))

        for tmpl in self:
            # Check 1: Restricted brand tags
            restricted_by_brand = any(
                t.name.startswith(RESTRICTED_BRAND_PREFIX) for t in tmpl.product_tag_ids
            )

            # Check 2: Restricted by EAN/SKU
            restricted_by_ean = False
            # Check template barcode
            if tmpl.barcode and tmpl.barcode in restricted_eans:
                restricted_by_ean = True
            # Check variant default codes
            if not restricted_by_ean:
                for variant in tmpl.product_variant_ids:
                    if variant.default_code and variant.default_code in restricted_eans:
                        restricted_by_ean = True
                        break

            tmpl.is_discount_restricted = restricted_by_brand or restricted_by_ean
