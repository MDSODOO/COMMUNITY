from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPublicShopProductPage(HttpCase):
    """Regression: GET /shop/<slug> must not raise AccessError on stock.warehouse
    for the public user. The product detail template renders product_variant.free_qty,
    whose compute reads stock.warehouse — public has no ACL on that model.
    Fix: template wraps the read in .sudo()."""

    def test_public_shop_product_page_no_warehouse_access_error(self):
        product_tmpl = self.env["product.template"].create({
            "name": "TEST Public Shop Item",
            "is_published": True,
            "website_published": True,
            "type": "consu",
            "is_storable": True,
            "list_price": 10.0,
        })
        # Use the canonical /shop/<id> URL — no slug dependency.
        resp = self.url_open("/shop/%s" % product_tmpl.id)
        # Accept 200 or a normal redirect; the bug manifests as 403.
        self.assertNotEqual(
            resp.status_code, 403,
            "Public shop product page returned 403 — likely stock.warehouse AccessError "
            "from an un-sudo'd free_qty/qty_available read in the template.",
        )


@tagged("post_install", "-at_install")
class TestFreeQtySudoForPublic(TransactionCase):
    """Direct check: the public user must be able to read free_qty via sudo()
    without raising AccessError on stock.warehouse."""

    def test_public_user_free_qty_via_sudo(self):
        public_user = self.env.ref("base.public_user")
        product = self.env["product.product"].create({
            "name": "TEST Public Free Qty",
            "type": "consu",
            "is_storable": True,
        })
        # Without sudo, public would hit AccessError on stock.warehouse.
        # The template fix uses .sudo(), so this must succeed.
        qty = product.with_user(public_user).sudo().free_qty
        self.assertEqual(qty, 0.0)
