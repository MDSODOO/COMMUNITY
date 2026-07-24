# -*- coding: utf-8 -*-
from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestStockScrapBatch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Medicine Depot PO Vendor',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Scrap Batch Test Product',
            'type': 'product',
        })
        cls.other_product = cls.env['product.product'].create({
            'name': 'Scrap Batch Other Product',
            'type': 'product',
        })
        cls.lot = cls.env['stock.lot'].create({
            'name': 'LOT-SCRAP-001',
            'product_id': cls.product.id,
            'company_id': cls.company.id,
        })
        cls.other_lot = cls.env['stock.lot'].create({
            'name': 'LOT-SCRAP-002',
            'product_id': cls.other_product.id,
            'company_id': cls.company.id,
        })
        cls.reason_caducidad = cls.env['stock.scrap.reason.tag'].create({
            'name': 'Caducidad',
            'sequence': 5,
        })
        cls.reason_merma = cls.env['stock.scrap.reason.tag'].create({
            'name': 'Merma',
            'sequence': 10,
        })
        cls.purchase_order = cls.env['purchase.order'].create({
            'partner_id': cls.vendor.id,
            'company_id': cls.company.id,
            'currency_id': cls.currency.id,
            'date_order': fields.Datetime.now(),
            'order_line': [
                Command.create({
                    'name': cls.product.display_name,
                    'product_id': cls.product.id,
                    'product_qty': 5.0,
                    'product_uom_id': cls.product.uom_id.id,
                    'price_unit': 12.34,
                    'lot_id': cls.lot.id,
                    'date_planned': fields.Datetime.now(),
                }),
            ],
        })
        cls.purchase_order.button_confirm()

    def test_purchase_lot_cost_uses_matching_purchase_line(self):
        batch = self.env['stock.scrap.batch'].create({
            'company_id': self.company.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'lot_id': self.lot.id,
                    'scrap_qty': 2.0,
                }),
                Command.create({
                    'product_id': self.other_product.id,
                    'lot_id': self.other_lot.id,
                    'scrap_qty': 1.0,
                }),
            ],
        })

        matched_line = batch.line_ids.filtered(lambda line: line.lot_id == self.lot)
        unmatched_line = batch.line_ids.filtered(lambda line: line.lot_id == self.other_lot)

        self.assertAlmostEqual(matched_line.purchase_lot_cost, 12.34, places=2)
        self.assertEqual(unmatched_line.purchase_lot_cost, 0.0)
        self.assertEqual(matched_line.currency_id, self.currency)

    def test_validate_batch_propagates_native_scrap_reason_tags(self):
        batch = self.env['stock.scrap.batch'].create({
            'company_id': self.company.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'lot_id': self.lot.id,
                    'scrap_qty': 1.0,
                    'scrap_reason_tag_ids': [
                        Command.set((self.reason_caducidad | self.reason_merma).ids)
                    ],
                }),
            ],
        })

        batch.action_request_validation()
        batch.sudo().action_validate_batch()

        scrap = batch.line_ids.scrap_id
        self.assertTrue(scrap)
        self.assertEqual(
            set(scrap.scrap_reason_tag_ids.ids),
            {self.reason_caducidad.id, self.reason_merma.id},
        )

    def test_backend_view_and_report_include_new_elements(self):
        form_arch = self.env.ref(
            'medicine_depot_scrap_batch.view_stock_scrap_batch_form'
        ).arch_db
        report_arch = self.env.ref(
            'medicine_depot_scrap_batch.report_scrap_batch'
        ).arch_db
        header_arch = self.env.ref(
            'medicine_depot_scrap_batch.pharma_scrap_batch_layout_header'
        ).arch_db
        legacy_report_arch = self.env.ref(
            'medicine_depot_scrap_batch.report_scrap_history_legacy'
        ).arch_db
        legacy_form_arch = self.env.ref(
            'medicine_depot_scrap_batch.view_medicine_depot_scrap_history_legacy_form'
        ).arch_db
        legacy_report = self.env.ref(
            'medicine_depot_scrap_batch.action_report_medicine_depot_scrap_history'
        )

        self.assertIn('purchase_lot_cost', form_arch)
        self.assertIn('scrap_reason_tag_ids', form_arch)
        self.assertIn('Historial legado de bajas', form_arch)
        self.assertIn('Historial de secuencias', form_arch)
        self.assertIn('action_print_legacy_report', legacy_form_arch)
        self.assertEqual(legacy_report.report_name, 'medicine_depot_scrap_batch.report_scrap_history_legacy')
        self.assertIn('medicine.depot.scrap.history', header_arch)
        self.assertIn("t-if=\"_sb._name == 'medicine.depot.scrap.history'\"", header_arch)
        self.assertIn('date_done', header_arch)
        self.assertIn('Líneas de Producto', legacy_report_arch)
        self.assertIn('Motivo de la baja', legacy_report_arch)
        self.assertIn('Total de líneas', legacy_report_arch)
        self.assertIn('Registro generado por', legacy_report_arch)
        self.assertIn('Entrega', legacy_report_arch)
        self.assertIn('Recibe', legacy_report_arch)
        self.assertIn('Motivo de la baja', report_arch)
        self.assertNotIn('<th>Motivo</th>', report_arch)
        self.assertIn('margin-top: 4rem', report_arch)

    def test_line_expiration_date_comes_from_lot(self):
        expected_expiration = fields.Datetime.now()
        self.lot.write({'expiration_date': expected_expiration})

        batch = self.env['stock.scrap.batch'].create({
            'company_id': self.company.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'lot_id': self.lot.id,
                    'scrap_qty': 1.0,
                }),
            ],
        })

        self.assertEqual(batch.line_ids.expiration_date, expected_expiration)

    def test_scrap_history_includes_done_records(self):
        other_location = self.env['stock.location'].create({
            'name': 'Scrap History Extra Location',
            'usage': 'internal',
            'company_id': self.company.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
        })
        old_scrap = self.env['stock.scrap'].create({
            'name': 'SP/00999',
            'company_id': self.company.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'scrap_qty': 1.0,
            'lot_id': self.lot.id,
            'location_id': other_location.id,
            'scrap_location_id': self.env.ref('stock.stock_location_scrapped').id,
            'state': 'done',
            'date_done': fields.Datetime.now(),
        })

        batch = self.env['stock.scrap.batch'].create({
            'company_id': self.company.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'lot_id': self.lot.id,
                    'scrap_qty': 1.0,
                }),
            ],
        })

        self.assertIn(old_scrap.id, batch.scrap_history_ids.ids)

    def test_legacy_history_model_exposes_done_scrap(self):
        expected_expiration = fields.Datetime.now()
        self.lot.write({'expiration_date': expected_expiration})

        batch = self.env['stock.scrap.batch'].create({
            'company_id': self.company.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'lot_id': self.lot.id,
                    'scrap_qty': 1.0,
                }),
            ],
        })
        batch.action_request_validation()
        batch.sudo().action_validate_batch()

        legacy = self.env['medicine.depot.scrap.history'].search([
            ('name', '=', batch.line_ids.scrap_id.name),
            ('product_id', '=', self.product.id),
            ('scrap_qty', '=', 1.0),
            ('company_id', '=', self.company.id),
        ], limit=1)

        self.assertTrue(legacy)
        self.assertEqual(legacy.product_id, self.product)
        self.assertEqual(legacy.lot_id, self.lot)
        self.assertEqual(legacy.expiration_date, expected_expiration)
        self.assertTrue(legacy.create_uid)
        self.assertAlmostEqual(legacy.purchase_lot_cost, 12.34, places=2)
        self.assertAlmostEqual(legacy.scrap_total_cost, 12.34, places=2)
        report_action = legacy.action_print_legacy_report()
        self.assertEqual(
            report_action.get('report_name'),
            'medicine_depot_scrap_batch.report_scrap_history_legacy',
        )
