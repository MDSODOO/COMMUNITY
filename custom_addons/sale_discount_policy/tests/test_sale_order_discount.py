from psycopg2 import IntegrityError
from odoo.tools import mute_logger
from .common import DiscountPolicyCommon


class TestSaleOrderDiscount(DiscountPolicyCommon):
    """Integration tests for sale order discount application."""

    def test_discount_applies_to_group_member_correct_branch(self):
        """Discount applies when order is from Farmacias Económicas in Cancún."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner_fe.id,
            'warehouse_id': self.warehouse_cancun.id,
        })

        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_generic.id,
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
        })

        # Trigger discount computation
        line._compute_discount()

        # Discount should be applied (2.0%)
        self.assertAlmostEqual(line.discount, 2.0, places=2)

    def test_no_discount_for_restricted_brand(self):
        """Discount is cleared for restricted brand products."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner_fe.id,
            'warehouse_id': self.warehouse_cancun.id,
        })

        # Create product with restricted brand tag
        product_restricted = self.env['product.product'].create({
            'name': 'Restricted Brand Product',
            'default_code': 'RESTRICTED_BRAND_001',
            'list_price': 100.0,
            'product_tmpl_id': self.env['product.template'].create({
                'name': 'Restricted Template',
                'product_tag_ids': [(4, self.tag_abbott.id)],
            }).id,
        })

        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': product_restricted.id,
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
        })

        line._compute_discount()

        # Discount should be cleared (0%)
        self.assertEqual(line.discount, 0.0)

    def test_no_discount_for_non_group_customer(self):
        """Discount does not apply to customers not in Farmacias Económicas group."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner_normal.id,
            'warehouse_id': self.warehouse_cancun.id,
        })

        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_generic.id,
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
        })

        line._compute_discount()

        # No discount should be applied
        self.assertEqual(line.discount, 0.0)

    def test_no_discount_for_wrong_warehouse(self):
        """Discount does not apply in unauthorized warehouses."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner_fe.id,
            'warehouse_id': self.warehouse_cdmx.id,  # CDMX not authorized
        })

        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_generic.id,
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
        })

        line._compute_discount()

        # No discount should be applied
        self.assertEqual(line.discount, 0.0)

    def test_discount_reason_computation(self):
        """Discount reason is correctly computed and stored."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner_fe.id,
            'warehouse_id': self.warehouse_cancun.id,
        })

        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_generic.id,
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
        })

        # Compute discount reasons
        line._compute_discount_reason()

        # Reason should indicate applied discount
        self.assertEqual(line.discount_reason, 'APPLIED')

    def test_product_is_discount_restricted_computed(self):
        """Product is_discount_restricted field is computed correctly for brand tags."""
        product_with_restricted_tag = self.env['product.product'].create({
            'name': 'Product with Restricted Tag',
            'default_code': 'TAGGED001',
            'list_price': 100.0,
            'product_tmpl_id': self.env['product.template'].create({
                'name': 'Tagged Template',
                'product_tag_ids': [(4, self.tag_bayer.id)],
            }).id,
        })

        tmpl = product_with_restricted_tag.product_tmpl_id
        self.assertTrue(tmpl.is_discount_restricted)

        # Generic product should not be marked restricted
        self.assertFalse(self.product_generic.product_tmpl_id.is_discount_restricted)

    def test_product_is_discount_restricted_by_ean(self):
        """Product is_discount_restricted reflects restriction by EAN/SKU."""
        # Create restricted SKU entry
        self.env['sale.restricted.sku'].create({
            'ean': 'RESTRICTED_BY_EAN_001',
            'marca': 'TEST',
            'nombre': 'Test Product',
        })

        # Product with restricted EAN
        product_restricted = self.env['product.product'].create({
            'name': 'Product Restricted by EAN',
            'default_code': 'EAN_RESTRICTED_001',
            'barcode': 'RESTRICTED_BY_EAN_001',
            'list_price': 100.0,
        })

        tmpl = product_restricted.product_tmpl_id
        self.assertTrue(tmpl.is_discount_restricted)

        # Product with unrestricted EAN
        product_allowed = self.env['product.product'].create({
            'name': 'Product Allowed',
            'default_code': 'EAN_ALLOWED_001',
            'barcode': 'ALLOWED_EAN_001',
            'list_price': 100.0,
        })

        tmpl_allowed = product_allowed.product_tmpl_id
        self.assertFalse(tmpl_allowed.is_discount_restricted)

    def test_onchange_warns_on_restricted_product(self):
        """On-change warning is raised when restricted product is added."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner_fe.id,
            'warehouse_id': self.warehouse_cancun.id,
        })

        line = self.env['sale.order.line'].new({
            'order_id': order,
            'product_id': self.product_bayer.id,
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
        })

        # Call onchange to check for warning
        result = line._onchange_warn_discount_restricted()

        # Should return a warning dict
        self.assertIsNotNone(result)
        self.assertIn('warning', result)
        self.assertIn('title', result['warning'])



class TestRestrictedSku(DiscountPolicyCommon):
    """Tests for restricted SKU model and EAN-based discount blocking."""

    def test_create_restricted_sku(self):
        """Create a restricted SKU record."""
        sku = self.env['sale.restricted.sku'].create({
            'ean': '7501033954061',
            'marca': 'ABBOTT',
            'nombre': 'ENSURE CHOCOLATE C/237ML',
        })
        self.assertEqual(sku.ean, '7501033954061')
        self.assertEqual(sku.marca, 'ABBOTT')

    @mute_logger('odoo.sql_db')
    def test_unique_ean_constraint(self):
        """EAN must be unique."""
        self.env['sale.restricted.sku'].create({
            'ean': '7501033954061',
            'marca': 'ABBOTT',
        })
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env['sale.restricted.sku'].create({
                    'ean': '7501033954061',
                    'marca': 'DIFFERENT',
                })

    def test_discount_blocked_by_restricted_ean(self):
        """Discount is cleared when product barcode is in restricted SKU list."""
        self.env['sale.restricted.sku'].create({
            'ean': 'TEST_EAN_001',
            'marca': 'TEST',
            'nombre': 'Test Product',
        })

        product = self.env['product.product'].create({
            'name': 'Test Restricted EAN Product',
            'default_code': 'TEST001',
            'list_price': 100.0,
            'barcode': 'TEST_EAN_001',
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner_fe.id,
            'warehouse_id': self.warehouse_cancun.id,
        })

        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': product.id,
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
        })

        line._compute_discount()

        self.assertEqual(line.discount, 0.0)

    def test_discount_applies_when_ean_not_restricted(self):
        """Discount applies normally when product EAN is not in restricted list."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner_fe.id,
            'warehouse_id': self.warehouse_cancun.id,
        })

        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_generic.id,
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
        })

        line._compute_discount()

        self.assertAlmostEqual(line.discount, 2.0, places=2)

    def test_discount_blocked_by_default_code_when_no_barcode(self):
        """Discount blocked when default_code is in restricted list (no barcode)."""
        # Create restricted SKU entry with default_code (no barcode)
        self.env['sale.restricted.sku'].create({
            'ean': 'DEFAULT_CODE_RESTRICTED',
            'marca': 'TEST',
            'nombre': 'Test Product',
        })

        # Create product with only default_code (no barcode)
        product = self.env['product.product'].create({
            'name': 'Restricted by Default Code',
            'default_code': 'DEFAULT_CODE_RESTRICTED',
            'list_price': 100.0,
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner_fe.id,
            'warehouse_id': self.warehouse_cancun.id,
        })

        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': product.id,
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
        })

        line._compute_discount()

        # Should be blocked even though product has no barcode
        self.assertEqual(line.discount, 0.0)
        self.assertEqual(line.discount_reason, 'RESTRICTED_SKU')

    def test_discount_blocked_by_barcode_when_default_code_not_restricted(self):
        """Discount blocked when barcode is restricted, even if default_code is not."""
        # Create restricted SKU entry with barcode
        self.env['sale.restricted.sku'].create({
            'ean': 'BARCODE_RESTRICTED',
            'marca': 'TEST',
            'nombre': 'Test Product',
        })

        # Create product with both codes, only barcode is restricted
        product = self.env['product.product'].create({
            'name': 'Restricted by Barcode',
            'default_code': 'DEFAULT_CODE_OK',
            'barcode': 'BARCODE_RESTRICTED',
            'list_price': 100.0,
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner_fe.id,
            'warehouse_id': self.warehouse_cancun.id,
        })

        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': product.id,
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
        })

        line._compute_discount()

        # Should be blocked because barcode is restricted
        self.assertEqual(line.discount, 0.0)
        self.assertEqual(line.discount_reason, 'RESTRICTED_SKU')
