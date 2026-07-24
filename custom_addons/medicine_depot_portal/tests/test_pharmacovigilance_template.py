# -*- coding: utf-8 -*-
import re

from odoo.tests.common import HttpCase


class PharmacovigilanceTemplateTest(HttpCase):
    """Pruebas smoke para la página pública de farmacovigilancia."""

    def setUp(self):
        super().setUp()
        self.url = "/farmacovigilancia"

    def test_01_page_loads(self):
        response = self.url_open(self.url, timeout=60)
        self.assertEqual(response.status_code, 200)

    def test_02_contains_wizard_markup(self):
        response = self.url_open(self.url, timeout=60)
        content = response.text

        self.assertIn("pharmacovigilance_form", content)
        self.assertIn("data-pv-step=\"1\"", content)
        self.assertIn("data-pv-step=\"6\"", content)
        self.assertIn("pharmacovigilance_success_screen", content)

    def test_03_post_creates_report(self):
        get_response = self.url_open(self.url, timeout=60)
        self.assertEqual(get_response.status_code, 200)
        csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', get_response.text)
        self.assertIsNotNone(csrf_match, "No se encontró csrf_token en el formulario")

        email = "qa.pharmacovigilance@medicinedepot.test"
        post_data = {
            "csrf_token": csrf_match.group(1),
            "patient_name": "Paciente QA",
            "patient_age": "42",
            "patient_sex": "female",
            "patient_city": "Mérida, Yucatán",
            "event_date": "2026-05-25",
            "event_severity": "moderate",
            "event_outcome": "recovering",
            "event_description": "Prueba smoke de farmacovigilancia.",
            "suspected_product_name": "Producto QA",
            "suspected_product_presentation": "Tabletas",
            "suspected_batch": "LOT-001",
            "suspected_dose": "1 tableta al día",
            "medical_history": "Sin antecedentes relevantes.",
            "current_condition": "Evolución estable.",
            "concomitant_medication": "Ninguno.",
            "notes": "Sin observaciones adicionales.",
            "reporter_name": "Reportero QA",
            "reporter_role": "patient",
            "reporter_relationship": "self",
            "reporter_email": email,
            "reporter_phone": "9990000000",
            "consent": "on",
        }

        post_response = self.url_open(self.url, data=post_data, timeout=120)
        self.assertEqual(post_response.status_code, 200)
        payload = post_response.json()
        self.assertTrue(payload.get("success"))
        self.assertTrue(payload.get("reference"))

        report = self.env["medicine.depot.pharmacovigilance.report"].sudo().search(
            [("reporter_email", "=", email)],
            limit=1,
        )
        self.assertTrue(report, "No se creó el reporte de farmacovigilancia")
        self.assertEqual(report.patient_name, "Paciente QA")
        self.assertEqual(report.event_severity, "moderate")
        self.assertEqual(report.state, "submitted")
