# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestSatDownloadRequest(TransactionCase):

    def setUp(self):
        super().setUp()
        self.today = date.today()
        self.Request = self.env['sat.download.request']

    def _make_request(self, **kw):
        vals = {
            'date_from': self.today - timedelta(days=30),
            'date_to': self.today,
            'download_type': 'received',
            'request_type': 'CFDI',
        }
        vals.update(kw)
        return self.Request.create(vals)

    def test_new_request_is_draft(self):
        req = self._make_request()
        self.assertEqual(req.state, 'draft')

    def test_name_assigned_from_sequence(self):
        req = self._make_request()
        self.assertTrue(req.name)
        self.assertNotEqual(req.name, 'Nueva Solicitud')

    def test_date_constraint_raises_when_from_after_to(self):
        with self.assertRaises(Exception):
            self._make_request(
                date_from=self.today,
                date_to=self.today - timedelta(days=1),
            )

    def test_action_send_request_raises_if_not_draft(self):
        req = self._make_request()
        req.state = 'requested'
        with self.assertRaises(UserError):
            req.action_send_request()

    def test_action_retry_resets_to_draft(self):
        req = self._make_request()
        req.write({
            'state': 'error',
            'sat_request_id': 'SAT-001',
            'error_message': 'Timeout',
            'verify_attempts': 5,
        })
        req.action_retry()
        self.assertEqual(req.state, 'draft')
        self.assertFalse(req.sat_request_id)
        self.assertFalse(req.error_message)
        self.assertEqual(req.verify_attempts, 0)

    def test_xml_count_computes_correctly(self):
        req = self._make_request()
        self.assertEqual(req.xml_count, 0)

    def test_action_view_xmls_returns_act_window(self):
        req = self._make_request()
        action = req.action_view_xmls()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'sat.xml.document')
        self.assertIn(('download_request_id', '=', req.id), action['domain'])


@tagged('post_install', '-at_install')
class TestSatXmlDocument(TransactionCase):

    def test_model_exists(self):
        self.assertIn('sat.xml.document', self.env)

    def test_sat_xml_document_has_uuid_field(self):
        self.assertIn('cfdi_uuid', self.env['sat.xml.document']._fields)

    def test_sat_xml_document_has_duplicate_flag(self):
        self.assertIn('is_duplicate', self.env['sat.xml.document']._fields)
