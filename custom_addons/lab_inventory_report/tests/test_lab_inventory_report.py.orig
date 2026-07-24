# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestLabInventoryReportModel(TransactionCase):
    """Tests para report.lab.inventory — modelo SQL view con detección dinámica."""

    def test_model_registered(self):
        self.assertIn('report.lab.inventory', self.env)

    def test_qty_a_la_mano_field_string(self):
        """Regla de negocio: el campo de inventario físico debe llamarse 'A la mano'."""
        field = self.env['report.lab.inventory']._fields.get('qty_a_la_mano')
        self.assertIsNotNone(field, "Falta el campo qty_a_la_mano")
        self.assertEqual(field.string, 'A la mano')

    def test_line_name_field_exists(self):
        self.assertIn('line_name', self.env['report.lab.inventory']._fields)

    def test_product_id_field_exists(self):
        self.assertIn('product_id', self.env['report.lab.inventory']._fields)

    def test_location_id_field_exists(self):
        self.assertIn('location_id', self.env['report.lab.inventory']._fields)

    def test_x_line_table_check_returns_bool(self):
        model = self.env['report.lab.inventory']
        result = model._x_line_table_exists()
        self.assertIsInstance(result, bool)

    def test_get_x_line_product_col_returns_none_or_string(self):
        model = self.env['report.lab.inventory']
        result = model._get_x_line_product_col()
        self.assertIn(type(result), [str, type(None)])

    def test_lab_names_constant_contains_serral(self):
        from odoo.addons.lab_inventory_report.models.report_lab_inventory import _LAB_NAMES
        self.assertIn('SERRAL', _LAB_NAMES)

    def test_search_does_not_raise(self):
        """La vista SQL debe ser consultable aunque esté vacía."""
        records = self.env['report.lab.inventory'].search([])
        self.assertIsNotNone(records)


@tagged('post_install', '-at_install')
class TestLabInventoryPdfReport(TransactionCase):

    def test_qweb_report_model_registered(self):
        self.assertIn(
            'report.lab_inventory_report.report_lab_inventory_pdf',
            self.env,
        )

    def test_get_report_values_empty(self):
        report = self.env['report.lab_inventory_report.report_lab_inventory_pdf']
        values = report._get_report_values([], data=None)
        self.assertIn('docs', values)
        self.assertIn('total_a_la_mano', values)
        self.assertEqual(values['total_a_la_mano'], 0.0)
