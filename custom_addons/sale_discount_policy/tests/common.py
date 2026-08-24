from odoo.tests import TransactionCase


class DiscountPolicyCommon(TransactionCase):
    """Base test case for discount policy module."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create partners
        cls.partner_fe = cls.env['res.partner'].create({
            'name': 'Farmacia Económica Test',
        })

        cls.partner_normal = cls.env['res.partner'].create({
            'name': 'Normal Customer',
        })

        # Create warehouses
        cls.warehouse_cancun = cls.env['stock.warehouse'].create({
            'name': 'Cancún',
            'code': 'CANCUN',
            'company_id': cls.env.company.id,
        })

        cls.warehouse_cdmx = cls.env['stock.warehouse'].create({
            'name': 'Ciudad de México',
            'code': 'CDMX',
            'company_id': cls.env.company.id,
        })

        # Create restricted brand tags
        cls.tag_bayer = cls.env['product.tag'].create({
            'name': 'MARCA_RESTRINGIDA_BAYER',
        })

        cls.tag_abbott = cls.env['product.tag'].create({
            'name': 'MARCA_RESTRINGIDA_ABBOTT',
        })

        # Create products
        cls.product_generic = cls.env['product.product'].create({
            'name': 'Generic Product',
            'default_code': 'GENERIC001',
            'list_price': 100.0,
        })

        cls.product_bayer = cls.env['product.product'].create({
            'name': 'Bayer Product',
            'default_code': 'BAYER001',
            'list_price': 100.0,
            'product_tmpl_id': cls.env['product.template'].create({
                'name': 'Bayer Product Template',
                'product_tag_ids': [(4, cls.tag_bayer.id)],
            }).id,
        })

        # Create discount policy with partner_ids instead of category
        cls.policy = cls.env['sale.discount.policy'].create({
            'name': 'Test Policy',
            'discount_pct': 2.0,
            'partner_ids': [(4, cls.partner_fe.id)],
            'warehouse_ids': [(4, cls.warehouse_cancun.id)],
            'company_id': cls.env.company.id,
        })
