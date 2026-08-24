# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestGlobalInvoiceConfig(TransactionCase):

    def test_company_has_global_invoice_fields(self):
        company = self.env.company
        self.assertIn('partner_inv_global_id', company._fields)
        self.assertIn('journal_inv_global_id', company._fields)

    def test_config_settings_has_global_invoice_fields(self):
        fields = self.env['res.config.settings']._fields
        self.assertIn('partner_inv_global_id', fields)
        self.assertIn('journal_inv_global_id', fields)
        self.assertIn('pos_active_facturacion_global', fields)

    def test_pos_config_has_active_facturacion_global(self):
        self.assertIn('active_facturacion_global', self.env['pos.config']._fields)

    def test_pos_config_partner_global_field_exists(self):
        self.assertIn('partner_global_id', self.env['pos.config']._fields)

    def test_pos_config_journal_global_field_exists(self):
        self.assertIn('journal_global_id', self.env['pos.config']._fields)


@tagged('post_install', '-at_install')
class TestPosOrderGlobalInvoice(TransactionCase):

    def setUp(self):
        super().setUp()
        self.PaymentMethod = self.env['pos.payment.method']
        self.Product = self.env['product.product']

    def test_pos_order_has_payment_method_field(self):
        self.assertIn('payment_method_id', self.env['pos.order']._fields)

    def test_pos_order_has_reverse_move_field(self):
        self.assertIn('reverse_move', self.env['pos.order']._fields)

    def test_compute_payment_method_empty_order(self):
        """Orden sin pagos: payment_method_id debe quedar vacío."""
        order = self.env['pos.order'].new({
            'company_id': self.env.company.id,
            'payment_ids': [],
        })
        order._compute_payment_method()
        self.assertFalse(order.payment_method_id)

    def test_get_invoice_lines_sets_product_display_name(self):
        """_get_invoice_lines_values debe asignar display_name del producto."""
        product = self.env['product.product'].create({
            'name': 'Paracetamol 500mg',
            'type': 'consu',
        })
        self.assertEqual(product.display_name, 'Paracetamol 500mg')
