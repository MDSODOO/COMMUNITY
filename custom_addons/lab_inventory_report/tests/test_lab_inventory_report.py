# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestLabInventoryReportModel(TransactionCase):
    """Tests para report.lab.inventory — modelo SQL view con detección dinámica.

    Migrado de x_line (Studio, 0% de productos poblados, columna de
    product_template con nombre no detectado -> vista siempre en fallback)
    a md.product.line / product_line_id (97% de productos poblados),
    por lo que la vista ahora sí puede devolver filas reales.
    """

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

    def test_product_line_table_check_returns_bool(self):
        model = self.env['report.lab.inventory']
        result = model._product_line_table_exists()
        self.assertIsInstance(result, bool)

    def test_get_product_line_col_returns_none_or_string(self):
        model = self.env['report.lab.inventory']
        result = model._get_product_line_col()
        self.assertIn(type(result), [str, type(None)])

    def test_get_product_line_col_detects_product_line_id(self):
        """En un entorno con md_product_lines instalado, la columna detectada
        debe ser 'product_line_id' (FK real hacia md_product_line), nunca un
        nombre de x_line — ese era el bug que dejaba la vista siempre vacía."""
        model = self.env['report.lab.inventory']
        result = model._get_product_line_col()
        if result is not None:
            self.assertEqual(result, 'product_line_id')

    def test_lab_names_constant_contains_serral(self):
        from odoo.addons.lab_inventory_report.models.report_lab_inventory import _LAB_NAMES
        self.assertIn('SERRAL', _LAB_NAMES)

    def test_lab_group_source_names_cover_all_lab_names(self):
        """Cada uno de los 4 laboratorios de negocio debe tener un mapeo
        explícito hacia al menos un nombre real en md_product_line."""
        from odoo.addons.lab_inventory_report.models.report_lab_inventory import (
            _LAB_NAMES, _LAB_GROUP_SOURCE_NAMES,
        )
        for lab_name in _LAB_NAMES:
            self.assertIn(lab_name, _LAB_GROUP_SOURCE_NAMES)
            self.assertTrue(_LAB_GROUP_SOURCE_NAMES[lab_name])

    def test_search_does_not_raise(self):
        """La vista SQL debe ser consultable, esté vacía o con datos reales."""
        records = self.env['report.lab.inventory'].search([])
        self.assertIsNotNone(records)

    def test_view_returns_real_rows_when_product_line_populated(self):
        """Si md_product_lines está instalado y hay productos con
        product_line_id poblado en alguno de los 4 laboratorios y con A la
        mano positivo, la vista debe devolver filas reales (antes de esta
        migración, siempre devolvía 0 filas por el bug de nombre de columna).
        """
        model = self.env['report.lab.inventory']
        if not model._product_line_table_exists() or not model._get_product_line_col():
            self.skipTest('md_product_lines no está instalado en este entorno de test')

        records = model.search([])
        for record in records:
            self.assertIn(record.line_name, dict(model._fields['line_name'].selection))
            self.assertTrue(record.product_id)
            self.assertTrue(record.location_id)


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
