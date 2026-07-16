# -*- coding: utf-8 -*-
from datetime import date, datetime

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCustomInvoiceFormatLogic(TransactionCase):
    """
    Tests de lógica pura del módulo custom_invoice_format.

    Cubre métodos que no requieren BD real: helpers de formateo y chunking.
    Regla de negocio aplicada: inventario físico = "A la mano".
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AccountMove = cls.env['account.move']
        # Busca cualquier factura existente para tener una instancia del modelo.
        # Si no existe, usa un browse() vacío — los métodos bajo prueba son
        # independientes del registro concreto.
        cls.dummy_invoice = cls.AccountMove.search(
            [('move_type', '=', 'out_invoice')], limit=1
        ) or cls.AccountMove

    # ------------------------------------------------------------------ #
    # _md_lot_quantity_to_float                                            #
    # ------------------------------------------------------------------ #

    def test_lot_qty_integer(self):
        self.assertAlmostEqual(
            self.AccountMove._md_lot_quantity_to_float(self.dummy_invoice, 5),
            5.0,
        )

    def test_lot_qty_float(self):
        self.assertAlmostEqual(
            self.AccountMove._md_lot_quantity_to_float(self.dummy_invoice, 2.5),
            2.5,
        )

    def test_lot_qty_string_dot(self):
        self.assertAlmostEqual(
            self.AccountMove._md_lot_quantity_to_float(self.dummy_invoice, '3.75'),
            3.75,
        )

    def test_lot_qty_string_comma(self):
        """Proveedores mexicanos suelen usar coma como separador decimal."""
        self.assertAlmostEqual(
            self.AccountMove._md_lot_quantity_to_float(self.dummy_invoice, '3,75'),
            3.75,
        )

    def test_lot_qty_negative_returns_absolute(self):
        self.assertAlmostEqual(
            self.AccountMove._md_lot_quantity_to_float(self.dummy_invoice, -10),
            10.0,
        )

    def test_lot_qty_none_returns_zero(self):
        self.assertAlmostEqual(
            self.AccountMove._md_lot_quantity_to_float(self.dummy_invoice, None),
            0.0,
        )

    def test_lot_qty_invalid_string_returns_zero(self):
        self.assertAlmostEqual(
            self.AccountMove._md_lot_quantity_to_float(self.dummy_invoice, 'N/A'),
            0.0,
        )

    # ------------------------------------------------------------------ #
    # md_chunk_cfdi_text                                                   #
    # ------------------------------------------------------------------ #

    def test_chunk_short_text_returns_single_item(self):
        result = self.dummy_invoice.md_chunk_cfdi_text('ABC', size=115)
        self.assertEqual(result, ['ABC'])

    def test_chunk_exact_size_returns_single_item(self):
        text = 'X' * 115
        result = self.dummy_invoice.md_chunk_cfdi_text(text, size=115)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], text)

    def test_chunk_long_text_splits_correctly(self):
        text = 'A' * 230
        result = self.dummy_invoice.md_chunk_cfdi_text(text, size=115)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(len(c) <= 115 for c in result))

    def test_chunk_empty_returns_dash(self):
        result = self.dummy_invoice.md_chunk_cfdi_text('', size=115)
        self.assertEqual(result, ['—'])

    def test_chunk_none_returns_dash(self):
        result = self.dummy_invoice.md_chunk_cfdi_text(None, size=115)
        self.assertEqual(result, ['—'])

    def test_chunk_invalid_size_uses_default(self):
        """Tamaño inválido cae al default (115) sin lanzar excepción."""
        text = 'B' * 50
        result = self.dummy_invoice.md_chunk_cfdi_text(text, size='invalid')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) >= 1)

    # ------------------------------------------------------------------ #
    # _md_format_lot_date                                                  #
    # ------------------------------------------------------------------ #

    def test_format_lot_date_date_object(self):
        d = date(2026, 12, 31)
        result = self.dummy_invoice._md_format_lot_date(d)
        self.assertEqual(result, '2026-12-31')

    def test_format_lot_date_datetime_object(self):
        dt = datetime(2026, 6, 15, 10, 30, 0)
        result = self.dummy_invoice._md_format_lot_date(dt)
        self.assertEqual(result, '2026-06-15')

    def test_format_lot_date_string_iso(self):
        result = self.dummy_invoice._md_format_lot_date('2026-03-01')
        self.assertEqual(result, '2026-03-01')

    def test_format_lot_date_none_returns_empty(self):
        result = self.dummy_invoice._md_format_lot_date(None)
        self.assertEqual(result, '')

    def test_format_lot_date_false_returns_empty(self):
        result = self.dummy_invoice._md_format_lot_date(False)
        self.assertEqual(result, '')

    # ------------------------------------------------------------------ #
    # _md_normalize_lot_text                                               #
    # ------------------------------------------------------------------ #

    def test_normalize_casefold(self):
        result = self.dummy_invoice._md_normalize_lot_text('PARACETAMOL 500MG')
        self.assertEqual(result, 'paracetamol 500mg')

    def test_normalize_collapses_spaces(self):
        result = self.dummy_invoice._md_normalize_lot_text('  producto   genérico  ')
        self.assertEqual(result, 'producto genérico')

    def test_normalize_none_returns_empty(self):
        result = self.dummy_invoice._md_normalize_lot_text(None)
        self.assertEqual(result, '')

    # ------------------------------------------------------------------ #
    # _md_empty_cfdi_values                                                #
    # ------------------------------------------------------------------ #

    def test_empty_cfdi_values_has_required_keys(self):
        values = self.dummy_invoice._md_empty_cfdi_values()
        required_keys = {
            'uuid', 'emisor_rfc', 'receptor_rfc',
            'sello_cfdi', 'sello_sat', 'cadena_original',
            'qr_value', 'qr_url', 'total',
        }
        for key in required_keys:
            self.assertIn(key, values, f"Clave faltante: {key}")

    def test_empty_cfdi_values_all_empty_strings(self):
        values = self.dummy_invoice._md_empty_cfdi_values()
        for key, val in values.items():
            self.assertEqual(val, '', f"Valor no vacío para clave: {key}")

    # ------------------------------------------------------------------ #
    # l10n_mx_cfdi_to_public field                                         #
    # ------------------------------------------------------------------ #

    def test_cfdi_to_public_field_exists(self):
        """Campo dummy que silencia AttributeError de l10n_mx_edi en Odoo 19."""
        self.assertIn('l10n_mx_cfdi_to_public', self.AccountMove._fields)

    def test_cfdi_to_public_default_false(self):
        field = self.AccountMove._fields['l10n_mx_cfdi_to_public']
        self.assertFalse(field.default(self.AccountMove))
