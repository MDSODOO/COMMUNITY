# -*- coding: utf-8 -*-
import base64
import io

from odoo.tests import TransactionCase, tagged

try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None


@tagged('post_install', '-at_install')
class TestProductSalePriceImport(TransactionCase):

    def _make_xlsx(self, rows):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        for row in rows:
            sheet.append(row)
        output = io.BytesIO()
        workbook.save(output)
        workbook.close()
        return base64.b64encode(output.getvalue())

    def test_preview_and_apply_base_sale_price(self):
        if openpyxl is None:
            self.skipTest('openpyxl is required')

        product = self.env['product.template'].create({
            'name': 'Producto de prueba',
            'default_code': 'SKU-PRICE-001',
            'list_price': 10.0,
        })
        wizard = self.env['product.sale.price.import.wizard'].create({
            'file': self._make_xlsx([
                ['SKU', 'Código de barras', 'Producto', 'Precio actual', 'Nuevo Precio'],
                ['SKU-PRICE-001', '', 'Producto de prueba', 10.0, 25.5],
            ]),
            'filename': 'precios.xlsx',
            'apply_mode': 'base',
        })

        wizard.action_preview()
        wizard.invalidate_recordset(['preview_line_ids', 'valid_lines'])
        self.assertEqual(wizard.valid_lines, 1)
        self.assertEqual(wizard.preview_line_ids.status, 'ok')

        wizard.action_apply()
        product.invalidate_recordset(['list_price'])
        self.assertAlmostEqual(product.list_price, 25.5, places=2)

        log = self.env['product.sale.price.import.log'].search([], limit=1)
        self.assertEqual(log.updated_count, 1)
        self.assertEqual(log.line_ids.status, 'updated')
