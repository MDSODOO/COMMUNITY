# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSalePurchaseMargins(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'QFM Margin Test Partner'})
        cls.product = cls.env['product.product'].create({
            'name': 'QFM Margin Test Product',
            'type': 'product',
            'standard_price': 60.0,
            'list_price': 100.0,
        })
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
        })
        cls.purchase_order = cls.env['purchase.order'].create({
            'partner_id': cls.partner.id,
        })

    def test_sale_margin_uses_discount_and_assigns_new_line(self):
        line = self.env['sale.order.line'].new({
            'order_id': self.sale_order.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'product_uom_qty': 2.0,
            'price_unit': 100.0,
            'discount': 10.0,
        })

        line._compute_qfm_sale_margin()

        self.assertAlmostEqual(line.qfm_margin_pct, 33.333333, places=4)
        self.assertAlmostEqual(line.qfm_margin_abs, 60.0, places=2)

    def test_sale_margin_zero_price_is_safe(self):
        line = self.env['sale.order.line'].new({
            'order_id': self.sale_order.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'product_uom_qty': 1.0,
            'price_unit': 0.0,
        })

        line._compute_qfm_sale_margin()

        self.assertEqual(line.qfm_margin_pct, 0.0)
        self.assertAlmostEqual(line.qfm_margin_abs, -60.0, places=2)

    def test_purchase_margin_positive_when_buying_below_standard_cost(self):
        line = self.env['purchase.order.line'].new({
            'order_id': self.purchase_order.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'product_qty': 3.0,
            'price_unit': 50.0,
        })

        line._compute_qfm_purchase_margin()

        self.assertAlmostEqual(line.qfm_margin_pct, 20.0, places=2)
        self.assertAlmostEqual(line.qfm_margin_abs, 30.0, places=2)

    def test_purchase_margin_negative_when_buying_above_standard_cost(self):
        line = self.env['purchase.order.line'].new({
            'order_id': self.purchase_order.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'product_qty': 1.0,
            'price_unit': 75.0,
        })

        line._compute_qfm_purchase_margin()

        self.assertAlmostEqual(line.qfm_margin_pct, -20.0, places=2)
        self.assertAlmostEqual(line.qfm_margin_abs, -15.0, places=2)

    def test_sale_target_margin_updates_price_unit_without_discount(self):
        line = self.env['sale.order.line'].new({
            'order_id': self.sale_order.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'product_uom_qty': 1.0,
            'price_unit': 0.0,
            'discount': 0.0,
            'qfm_margin_pct': 40.0,
        })

        line._onchange_qfm_margin_pct_set_price_unit()

        self.assertAlmostEqual(line.price_unit, 100.0, places=2)

    def test_sale_target_margin_updates_price_unit_with_discount(self):
        line = self.env['sale.order.line'].new({
            'order_id': self.sale_order.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'product_uom_qty': 1.0,
            'price_unit': 0.0,
            'discount': 10.0,
            'qfm_margin_pct': 40.0,
        })

        line._onchange_qfm_margin_pct_set_price_unit()

        self.assertAlmostEqual(line.price_unit, 111.11, places=2)

    def test_sale_target_margin_100_raises_validation_error(self):
        line = self.env['sale.order.line'].new({
            'order_id': self.sale_order.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
            'discount': 0.0,
            'qfm_margin_pct': 100.0,
        })

        with self.assertRaises(ValidationError):
            line._inverse_qfm_margin_pct()

    def test_sale_target_margin_negative_raises_validation_error(self):
        line = self.env['sale.order.line'].new({
            'order_id': self.sale_order.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
            'discount': 0.0,
            'qfm_margin_pct': -10.0,
        })

        with self.assertRaises(ValidationError):
            line._inverse_qfm_margin_pct()

    def test_sale_target_margin_without_standard_cost_raises(self):
        product_sin_costo = self.env['product.product'].create({
            'name': 'QFM Producto Sin Costo',
            'type': 'product',
            'standard_price': 0.0,
            'list_price': 0.0,
        })
        line = self.env['sale.order.line'].new({
            'order_id': self.sale_order.id,
            'product_id': product_sin_costo.id,
            'product_uom_id': product_sin_costo.uom_id.id,
            'product_uom_qty': 1.0,
            'price_unit': 50.0,
            'discount': 0.0,
            'qfm_margin_pct': 30.0,
        })

        with self.assertRaises(ValidationError):
            line._inverse_qfm_margin_pct()

    def test_margin_rule_lookup_is_normalized(self):
        self.env['qfm.sale.margin.line.rule'].create({
            'line_name': 'PISA ELECTROLIT Y ELECTROLIFE',
            'margin_pct': 17.0,
        })

        margin = self.env['qfm.sale.margin.line.rule'].get_margin_for_line_name(
            '  pisa   electrolit y electrolife  '
        )
        self.assertAlmostEqual(margin, 17.0, places=2)

    def test_margin_rule_lookup_is_company_scoped_with_global_fallback(self):
        rules_model = self.env['qfm.sale.margin.line.rule']
        line_name = 'LINEA MULTI COMPANY TEST'
        company_a = self.env.company
        company_b = self.env['res.company'].create({'name': 'QFM Margin Company B'})
        company_c = self.env['res.company'].create({'name': 'QFM Margin Company C'})

        rules_model.create({
            'company_id': False,
            'line_name': line_name,
            'margin_pct': 11.0,
        })
        rules_model.create({
            'company_id': company_a.id,
            'line_name': line_name,
            'margin_pct': 19.0,
        })
        rules_model.create({
            'company_id': company_b.id,
            'line_name': line_name,
            'margin_pct': 23.0,
        })

        margin_company_a = rules_model.get_margin_for_line_name(
            line_name,
            company=company_a,
        )
        margin_company_b = rules_model.get_margin_for_line_name(
            line_name,
            company=company_b,
        )
        margin_company_c = rules_model.get_margin_for_line_name(
            line_name,
            company=company_c,
        )

        self.assertAlmostEqual(margin_company_a, 19.0, places=2)
        self.assertAlmostEqual(margin_company_b, 23.0, places=2)
        self.assertAlmostEqual(margin_company_c, 11.0, places=2)

    def test_margin_rule_rejects_margin_greater_or_equal_100(self):
        with self.assertRaises(ValidationError):
            self.env['qfm.sale.margin.line.rule'].create({
                'line_name': 'LINEA TEST',
                'margin_pct': 100.0,
            })

    def test_product_target_margin_rejects_out_of_range(self):
        product = self.env['product.template'].create({
            'name': 'QFM Producto Margen Rango',
            'standard_price': 50.0,
        })
        with self.assertRaises(ValidationError):
            product.qfm_target_margin_pct = 100.0
        with self.assertRaises(ValidationError):
            product.qfm_target_margin_pct = -5.0

    def test_product_target_margin_accepts_valid_range(self):
        product = self.env['product.template'].create({
            'name': 'QFM Producto Margen Valido',
            'standard_price': 50.0,
        })
        product.qfm_target_margin_pct = 0.0
        product.qfm_target_margin_pct = 50.0
        product.qfm_target_margin_pct = 99.99
        self.assertAlmostEqual(product.qfm_target_margin_pct, 99.99, places=2)

    def test_product_variant_action_apply_suggested_price_is_disabled(self):
        template = self.env['product.template'].create({
            'name': 'QFM Producto Bridge Variant',
            'standard_price': 80.0,
            'list_price': 100.0,
            'qfm_target_margin_pct': 20.0,
        })
        variant = template.product_variant_id
        expected_price = template.qfm_suggested_list_price
        self.assertGreater(expected_price, 0.0)

        result = variant.action_apply_suggested_price()

        self.assertEqual(result['tag'], 'display_notification')
        self.assertAlmostEqual(template.list_price, 100.0, places=2)

    def test_receipt_price_policy_helper(self):
        from odoo.addons.sale_purchase_margins.models.margin_tools import should_apply_price_update
        self.assertTrue(should_apply_price_update('always_update', 10.0, 9.0))
        self.assertFalse(should_apply_price_update('manual_review', 10.0, 12.0))
        self.assertTrue(should_apply_price_update('only_increase', 10.0, 12.0))
        self.assertFalse(should_apply_price_update('only_increase', 10.0, 8.0))

    def test_customer_return_incoming_without_purchase_does_not_reprice(self):
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'incoming')],
                limit=1,
            )
        self.assertTrue(picking_type, 'No existe un tipo de operación incoming para la prueba.')

        source_location = (
            picking_type.default_location_src_id
            or self.env.ref('stock.stock_location_suppliers')
        )
        dest_location = (
            picking_type.default_location_dest_id
            or self.env.ref('stock.stock_location_stock')
        )

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'company_id': self.env.company.id,
            'partner_id': self.partner.id,
        })

        with patch(
            'odoo.addons.sale_purchase_margins.models.stock_picking.'
            'StockPicking._qfm_update_sale_prices'
        ) as mocked_reprice:
            picking.write({'state': 'done'})
            mocked_reprice.assert_not_called()
