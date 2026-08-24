from odoo import api


def migrate(cr, version):
    """Tag products that match restricted SKU codes (post-install)."""
    env = api.Environment(cr, 1, {})  # Use superuser (ID=1)

    # Get or create the restriction tag
    tag_model = env['product.tag']
    sku_tag = tag_model.search([('name', '=', 'SKU_RESTRINGIDO_EAN')], limit=1)
    if not sku_tag:
        sku_tag = tag_model.create({'name': 'SKU_RESTRINGIDO_EAN'})

    # Get all restricted SKU EANs
    restricted_skus = env['sale.restricted.sku'].search([])
    restricted_eans = set(restricted_skus.mapped('ean'))

    if not restricted_eans:
        return

    # Find and tag products matching restricted SKUs
    product_model = env['product.product']

    # Search for products by barcode
    for ean in restricted_eans:
        products = product_model.search([('barcode', '=', ean)])
        for product in products:
            if sku_tag not in product.product_tmpl_id.product_tag_ids:
                product.product_tmpl_id.product_tag_ids = [(4, sku_tag.id)]

    env.cr.commit()
