from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestPhase1Templates(HttpCase):
    """Smoke tests for Phase 1 website templates."""

    def test_navbar_fragments_render(self):
        res = self.url_open("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"md-bento-topbar", res.content)
        self.assertIn(b"md-bento-nav", res.content)

    def test_sucursales_renders(self):
        res = self.url_open("/sucursales")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"md-gmap-container", res.content)

    def test_shop_renders(self):
        res = self.url_open("/shop")
        self.assertEqual(res.status_code, 200)

    def test_login_renders_with_form(self):
        """Item 7 · /login responde 200 y sirve el formulario nativo intacto.

        Si el bundle web.assets_frontend fallara la compilación, la página
        seguiría devolviendo 200 pero el HTML no incluiría el formulario; por
        eso validamos también la presencia del marcador oe_login_form.
        """
        res = self.url_open("/web/login")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"oe_login_form", res.content)

    def test_sucursales_weekend_schedule_markup(self):
        """Item 22 · la vista de sucursales expone los datos de horario que el
        badge Abierto/Cerrado necesita para evaluar fin de semana en el cliente.
        """
        res = self.url_open("/sucursales")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"md-branch-status", res.content)
