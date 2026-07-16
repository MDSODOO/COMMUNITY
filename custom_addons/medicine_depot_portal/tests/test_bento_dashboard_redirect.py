# -*- coding: utf-8 -*-
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestBentoDashboardRedirect(HttpCase):
    """Tests unitarios y HTTP para el redireccionamiento al dashboard Bento y navbar."""

    def test_01_dashboard_redirect_public(self):
        """Un usuario no logueado debe ser redirigido al login al intentar acceder."""
        res = self.url_open("/my/dashboard")
        self.assertTrue(res.status_code in (200, 302, 303))
        if res.status_code == 200:
            self.assertIn(b"login", res.content)

    def test_02_bento_redirect_public(self):
        """Un usuario no logueado debe ser redirigido al login al intentar acceder a /my/bento."""
        res = self.url_open("/my/bento")
        self.assertTrue(res.status_code in (200, 302, 303))
        if res.status_code == 200:
            self.assertIn(b"login", res.content)

    def test_03_dashboard_authenticated(self):
        """Un usuario logueado puede acceder a /my/dashboard y /my/bento, renderizando el Bento portal."""
        self.authenticate("admin", "admin")
        
        # Probar /my/dashboard
        res = self.url_open("/my/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"md_bento_portal", res.content)
        self.assertIn(b"md_cards_grid", res.content)
        # Verificar la inyección del botón en el navbar
        self.assertIn(b"Mi Panel", res.content)
        self.assertIn(b"/my/dashboard", res.content)
        
        # Verificar la eliminación del botón "DM modo"
        self.assertNotIn(b"md-dark-toggle", res.content)
        self.assertNotIn(b"DM Modo", res.content)

        # Probar /my/bento
        res_bento = self.url_open("/my/bento")
        self.assertEqual(res_bento.status_code, 200)
        self.assertIn(b"md_bento_portal", res_bento.content)
        
        # Regla terminológica estricta de stock
        content_str = res.content.decode("utf-8")
        self.assertNotIn("Disponible", content_str)
        self.assertNotIn("disponible", content_str.lower())

    def test_04_profile_bento_cards(self):
        """Un usuario logueado puede acceder a /my/account y ver las tarjetas Bento del formulario."""
        self.authenticate("admin", "admin")
        res = self.url_open("/my/account")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"bento-card", res.content)
        self.assertIn(b"Datos Personales", res.content)
        self.assertIn(b"Direcci\xc3\xb3n y Env\xc3\xado", res.content)
        self.assertIn(b"Informaci\xc3\xb3n Comercial y Fiscal", res.content)
        self.assertIn(b"COFEPRIS (Expediente)", res.content)
        self.assertIn(b"Documentos Legales", res.content)

