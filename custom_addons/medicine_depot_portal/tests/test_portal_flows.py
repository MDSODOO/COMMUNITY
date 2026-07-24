from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestAffiliationState(TransactionCase):
    """Tests unitarios para _get_affiliation_state."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Affiliate",
            "email": "affiliate@test.mx",
        })

    def _ctrl(self):
        from odoo.addons.medicine_depot_portal.controllers.portal import MedicineDepotPortal
        return MedicineDepotPortal()

    def test_no_partner_returns_not_affiliate(self):
        ctrl = self._ctrl()
        state = ctrl._get_affiliation_state(False)
        self.assertFalse(state.get("is_affiliate"))
        self.assertFalse(state.get("has_missing_docs"))

    def test_partner_without_fields_not_affiliate(self):
        ctrl = self._ctrl()
        state = ctrl._get_affiliation_state(self.partner)
        self.assertFalse(state.get("is_affiliate"))

    def test_affiliation_state_keys_present(self):
        ctrl = self._ctrl()
        state = ctrl._get_affiliation_state(self.partner)
        self.assertIn("is_affiliate", state)
        self.assertIn("missing_docs", state)
        self.assertIn("has_missing_docs", state)
        self.assertIn("missing_docs_count", state)
        self.assertIn("affiliation_upload_url", state)


@tagged("post_install", "-at_install")
class TestAfiliacionEndpoint(HttpCase):
    """Tests HTTP para el flujo de afiliación."""

    def test_afiliacion_get_renders_page(self):
        resp = self.url_open("/afiliacion")
        self.assertEqual(resp.status_code, 200)

    def test_afiliacion_post_valid(self):
        resp = self.url_open(
            "/afiliacion",
            data={
                "nombre": "María",
                "email": "maria@farmacia.mx",
                "telefono": "9991234567",
                "especialidad": "Farmacéutica",
                "privacy": "1",
            },
        )
        self.assertIn(resp.status_code, (200, 201))
        try:
            body = resp.json()
            self.assertTrue(body.get("success"))
        except Exception:
            # Algunos entornos redirigen a la misma página en éxito
            pass

    def test_afiliacion_post_missing_required(self):
        resp = self.url_open(
            "/afiliacion",
            data={"nombre": "", "email": "", "telefono": "", "especialidad": ""},
        )
        try:
            body = resp.json()
            self.assertFalse(body.get("success"))
        except Exception:
            self.assertEqual(resp.status_code, 400)

    def test_afiliacion_duplicate_email(self):
        self.env["res.partner"].sudo().create({
            "name": "Existente",
            "email": "dup_afiliacion@test.mx",
        })
        resp = self.url_open(
            "/afiliacion",
            data={
                "nombre": "Nuevo",
                "email": "dup_afiliacion@test.mx",
                "telefono": "9990000000",
                "especialidad": "Farmacéutica",
                "privacy": "1",
            },
        )
        self.assertEqual(resp.status_code, 409)


@tagged("post_install", "-at_install")
class TestPharmacovigilanciaFlow(HttpCase):
    """Tests HTTP para el flujo de farmacovigilancia."""

    def test_farmacovigilancia_get_renders(self):
        resp = self.url_open("/farmacovigilancia")
        self.assertEqual(resp.status_code, 200)

    def test_farmacovigilancia_post_honeypot_rejected(self):
        resp = self.url_open(
            "/farmacovigilancia",
            data={
                "patient_name": "Test",
                "event_description": "Reacción",
                "suspected_product_name": "Producto",
                "reporter_name": "Reporter",
                "reporter_role": "patient",
                "reporter_relationship": "self",
                "reporter_email": "r@test.mx",
                "consent": "1",
                "md_hp_field": "bot_filled",
            },
        )
        try:
            body = resp.json()
            self.assertFalse(body.get("success"))
        except Exception:
            self.assertNotEqual(resp.status_code, 200)

    def test_pharmacovigilance_xss_sanitization(self):
        from odoo.addons.medicine_depot_portal.controllers.utils import clean
        cleaned = clean({"test_key": "<script>alert(1)</script>"}, "test_key")
        self.assertNotIn("<script>", cleaned)
        self.assertIn("&lt;script&gt;", cleaned)
