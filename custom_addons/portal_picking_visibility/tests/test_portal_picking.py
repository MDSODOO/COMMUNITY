from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPortalPickingDomain(TransactionCase):
    """Tests para _prepare_orders_domain y _compute_portal_delivery_status."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Portal Partner"})
        cls.product = cls.env["product.product"].create({
            "name": "Test Product",
            "type": "consu",
        })

    def test_compute_no_pickings(self):
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
        })
        self.assertEqual(order.portal_delivery_status, "no_delivery")
        self.assertFalse(order.has_active_pickings)

    def test_prepare_orders_domain_includes_base(self):
        """base_domain del super() debe incorporarse al dominio resultante."""
        from odoo.addons.portal_picking_visibility.controllers.portal import PortalPickingVisibility
        ctrl = PortalPickingVisibility()
        domain = ctrl._prepare_orders_domain(self.partner)
        domain_str = str(domain)
        self.assertIn("partner_id", domain_str)

    def test_compute_delivered_status(self):
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "state": "sale",
        })
        picking_type = self.env["stock.picking.type"].search([
            ("code", "=", "outgoing"),
        ], limit=1)
        if not picking_type:
            return
        location_out = self.env["stock.location"].search([("usage", "=", "customer")], limit=1)
        location_in = picking_type.default_location_src_id
        if not location_in or not location_out:
            return
        picking = self.env["stock.picking"].create({
            "partner_id": self.partner.id,
            "picking_type_id": picking_type.id,
            "location_id": location_in.id,
            "location_dest_id": location_out.id,
            "sale_id": order.id,
            "state": "done",
        })
        order._compute_portal_delivery_status()
        self.assertEqual(order.portal_delivery_status, "delivered")
        self.assertTrue(order.has_active_pickings)


@tagged("post_install", "-at_install")
class TestPortalPickingRoute(HttpCase):
    """Tests HTTP para /my/pickings."""

    def test_pickings_route_redirects_public(self):
        resp = self.url_open("/my/pickings")
        self.assertIn(resp.status_code, (200, 302, 303),
                      "Ruta /my/pickings debe redirigir a login o responder 200 con sesión")
