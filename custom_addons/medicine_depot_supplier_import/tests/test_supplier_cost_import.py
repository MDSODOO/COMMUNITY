# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSupplierCostImportLog(TransactionCase):
    """
    Tests del modelo de auditoría de importaciones de costos de proveedores.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Log = cls.env['supplier.cost.import.log']
        cls.LogLine = cls.env['supplier.cost.import.log.line']

    def _make_log(self, **kwargs):
        defaults = {
            'total_rows': 10,
            'updated': 7,
            'not_found': 2,
            'errors': 1,
            'summary': 'Importación de prueba',
        }
        defaults.update(kwargs)
        return self.Log.create(defaults)

    # ------------------------------------------------------------------ #
    # Creación de log                                                      #
    # ------------------------------------------------------------------ #

    def test_log_creation(self):
        log = self._make_log()
        self.assertTrue(log.id)
        self.assertEqual(log.total_rows, 10)
        self.assertEqual(log.updated, 7)
        self.assertEqual(log.not_found, 2)
        self.assertEqual(log.errors, 1)

    def test_log_date_auto_set(self):
        log = self._make_log()
        self.assertTrue(log.date)

    def test_log_user_auto_set(self):
        log = self._make_log()
        self.assertEqual(log.user_id, self.env.user)

    # ------------------------------------------------------------------ #
    # _compute_cost_change                                                 #
    # ------------------------------------------------------------------ #

    def test_cost_change_positive(self):
        log = self._make_log()
        line = self.LogLine.create({
            'log_id': log.id,
            'row_number': 1,
            'old_cost': 100.0,
            'new_cost': 120.0,
            'status': 'updated',
        })
        self.assertAlmostEqual(line.cost_change, 20.0)

    def test_cost_change_negative(self):
        log = self._make_log()
        line = self.LogLine.create({
            'log_id': log.id,
            'row_number': 2,
            'old_cost': 100.0,
            'new_cost': 80.0,
            'status': 'updated',
        })
        self.assertAlmostEqual(line.cost_change, -20.0)

    def test_cost_change_zero(self):
        log = self._make_log()
        line = self.LogLine.create({
            'log_id': log.id,
            'row_number': 3,
            'old_cost': 100.0,
            'new_cost': 100.0,
            'status': 'updated',
        })
        self.assertAlmostEqual(line.cost_change, 0.0)

    def test_cost_change_no_old_cost_returns_new_cost(self):
        """Sin costo anterior, el cambio debe ser igual al nuevo costo."""
        log = self._make_log()
        line = self.LogLine.create({
            'log_id': log.id,
            'row_number': 4,
            'old_cost': 0.0,
            'new_cost': 50.0,
            'status': 'updated',
        })
        self.assertAlmostEqual(line.cost_change, 50.0)

    # ------------------------------------------------------------------ #
    # Líneas con estado not_found y error                                  #
    # ------------------------------------------------------------------ #

    def test_not_found_line_creation(self):
        log = self._make_log()
        line = self.LogLine.create({
            'log_id': log.id,
            'row_number': 5,
            'barcode': '7501234567890',
            'product_name': 'Producto Inexistente',
            'status': 'not_found',
        })
        self.assertEqual(line.status, 'not_found')
        self.assertFalse(line.product_id)

    def test_error_line_with_message(self):
        log = self._make_log()
        line = self.LogLine.create({
            'log_id': log.id,
            'row_number': 6,
            'status': 'error',
            'error_message': 'ValueError: precio inválido',
        })
        self.assertEqual(line.status, 'error')
        self.assertIn('ValueError', line.error_message)

    # ------------------------------------------------------------------ #
    # Cascade delete                                                       #
    # ------------------------------------------------------------------ #

    def test_lines_cascade_deleted_with_log(self):
        log = self._make_log()
        line = self.LogLine.create({
            'log_id': log.id,
            'row_number': 1,
            'status': 'updated',
            'old_cost': 10.0,
            'new_cost': 12.0,
        })
        line_id = line.id
        log.unlink()
        self.assertFalse(self.LogLine.browse(line_id).exists())
