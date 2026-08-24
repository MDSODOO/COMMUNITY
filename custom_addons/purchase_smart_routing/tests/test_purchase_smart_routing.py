# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestPurchaseRoutingModel(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Routing = self.env['purchase.routing']

    def _make_routing(self, **kw):
        vals = {'date': '2026-06-10'}
        vals.update(kw)
        return self.Routing.create(vals)

    def test_new_routing_is_draft(self):
        r = self._make_routing()
        self.assertEqual(r.state, 'draft')

    def test_name_auto_assigned(self):
        r = self._make_routing()
        self.assertTrue(r.name)
        self.assertNotEqual(r.name, 'Nuevo')

    def test_routing_has_threshold_percent(self):
        self.assertIn('threshold_percent', self.Routing._fields)

    def test_routing_has_po_initial_state(self):
        self.assertIn('po_initial_state', self.Routing._fields)

    def test_routing_has_warehouse_field(self):
        self.assertIn('warehouse_id', self.Routing._fields)

    def test_summary_fields_start_at_zero(self):
        r = self._make_routing()
        self.assertEqual(r.total_products, 0)
        self.assertEqual(r.total_qty_demanded, 0.0)
        self.assertEqual(r.total_qty_satisfied, 0.0)
        self.assertEqual(r.total_qty_unsatisfied, 0.0)

    def test_po_count_starts_at_zero(self):
        r = self._make_routing()
        self.assertEqual(r.po_count, 0)

    def test_state_selection_values(self):
        states = dict(self.Routing._fields['state'].selection)
        self.assertIn('draft', states)
        self.assertIn('calculated', states)
        self.assertIn('confirmed', states)
        self.assertIn('done', states)


@tagged('post_install', '-at_install')
class TestRoutingConfig(TransactionCase):

    def test_routing_config_model_exists(self):
        self.assertIn('purchase.routing.config', self.env)

    def test_res_config_has_routing_threshold(self):
        fields = self.env['res.config.settings']._fields
        self.assertIn('routing_threshold_percent', fields)
