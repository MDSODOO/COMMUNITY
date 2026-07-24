from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class MdWebsiteApiTest(HttpCase):

    def test_afiliacion_submit_missing_fields(self):
        res = self.url_open(
            '/web/afiliacion/submit',
            data={'nombre': '', 'apellido': 'Test', 'email': 'bad', 'telefono': ''},
        )
        self.assertEqual(res.status_code, 400)
        body = res.json()
        self.assertFalse(body['success'])

    def test_medicd_submit_missing_nombre(self):
        res = self.url_open(
            '/web/medicd/submit',
            data={'nombre': '', 'email': 'test@example.com'},
        )
        self.assertEqual(res.status_code, 400)
        body = res.json()
        self.assertFalse(body['success'])

    def test_medicd_submit_ok(self):
        res = self.url_open(
            '/web/medicd/submit',
            data={
                'nombre': 'Ana',
                'apellido': 'García',
                'email': 'ana@farmacia.mx',
                'telefono': '5512345678',
                'tiene_farmacia': 'si',
                'direccion': 'Av. Insurgentes 100',
                'colonia': 'Roma Norte',
                'cp': '06700',
                'estado': 'CDMX',
                'tiene_proveedor': 'no',
            },
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body['success'])

    def test_afiliacion_get_not_allowed(self):
        """GET en endpoint POST debe devolver 405 o redirigir, no 200."""
        res = self.url_open('/web/afiliacion/submit')
        self.assertNotEqual(res.status_code, 200,
                            "GET en /web/afiliacion/submit no debe devolver 200")

    def test_medicd_get_not_allowed(self):
        res = self.url_open('/web/medicd/submit')
        self.assertNotEqual(res.status_code, 200,
                            "GET en /web/medicd/submit no debe devolver 200")

    def test_afiliacion_invalid_email(self):
        res = self.url_open(
            '/web/afiliacion/submit',
            data={'nombre': 'Juan', 'apellido': 'Pérez', 'email': 'no-es-email', 'telefono': '5500000000'},
        )
        self.assertEqual(res.status_code, 400)
        body = res.json()
        self.assertFalse(body['success'])

    def test_afiliacion_duplicate_email_rejected(self):
        """Segundo envío con mismo email debe devolver 409."""
        self.env['res.partner'].sudo().create({
            'name': 'Existente',
            'email': 'dup@test.mx',
        })
        res = self.url_open(
            '/web/afiliacion/submit',
            data={
                'nombre': 'Nuevo', 'apellido': 'Partner',
                'email': 'dup@test.mx', 'telefono': '5512345678',
                'privacy': '1',
            },
        )
        self.assertEqual(res.status_code, 409)
