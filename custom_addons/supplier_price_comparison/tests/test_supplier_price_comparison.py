# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestPriceComparisonProduct(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Product = self.env['price.comparison.product']
        self.Line = self.env['price.comparison.line']
        self.partner = self.env['res.partner'].create({'name': 'Proveedor Test'})

    def _make_product(self, barcode='PROD-001', name='Producto Test'):
        return self.Product.create({'barcode': barcode, 'name': name})

    def test_create_product(self):
        p = self._make_product()
        self.assertTrue(p.id)
        self.assertEqual(p.barcode, 'PROD-001')

    def test_unique_barcode_constraint(self):
        self._make_product(barcode='UNIQUE-BC')
        with self.assertRaises(Exception):
            self._make_product(barcode='UNIQUE-BC', name='Otro producto')

    def test_supplier_count_zero_without_lines(self):
        p = self._make_product()
        self.assertEqual(p.supplier_count, 0)

    def test_supplier_count_with_lines(self):
        p = self._make_product()
        self.Line.create({'product_id': p.id, 'supplier_id': self.partner.id, 'price': 50.0})
        p._compute_supplier_count()
        self.assertEqual(p.supplier_count, 1)

    def test_best_price_with_single_line(self):
        p = self._make_product()
        self.Line.create({'product_id': p.id, 'supplier_id': self.partner.id, 'price': 99.5})
        p._compute_best_price()
        self.assertAlmostEqual(p.best_price, 99.5)
        self.assertEqual(p.best_supplier_id, self.partner)

    def test_best_price_selects_lowest(self):
        p = self._make_product()
        partner2 = self.env['res.partner'].create({'name': 'Proveedor 2'})
        self.Line.create({'product_id': p.id, 'supplier_id': self.partner.id, 'price': 120.0})
        self.Line.create({'product_id': p.id, 'supplier_id': partner2.id, 'price': 95.0})
        p._compute_best_price()
        self.assertAlmostEqual(p.best_price, 95.0)
        self.assertEqual(p.best_supplier_id, partner2)

    def test_best_price_ignores_zero_price(self):
        p = self._make_product()
        self.Line.create({'product_id': p.id, 'supplier_id': self.partner.id, 'price': 0.0})
        p._compute_best_price()
        self.assertAlmostEqual(p.best_price, 0.0)
        self.assertFalse(p.best_supplier_id)

    def test_action_view_price_lines(self):
        p = self._make_product()
        action = p.action_view_price_lines()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'price.comparison.line')
        self.assertIn(('product_id', '=', p.id), action['domain'])


@tagged('post_install', '-at_install')
class TestPriceComparisonLine(TransactionCase):

    def test_model_exists(self):
        self.assertIn('price.comparison.line', self.env)

    def test_line_has_price_field(self):
        self.assertIn('price', self.env['price.comparison.line']._fields)

    def test_line_has_supplier_field(self):
        self.assertIn('supplier_id', self.env['price.comparison.line']._fields)
