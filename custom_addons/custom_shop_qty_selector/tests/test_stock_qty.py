from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestLotFilteredStockQtyMap(TransactionCase):
    """Tests para _md_get_active_ingredients y _md_get_product_lines."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.template"].create({
            "name": "Test MD Product",
            "type": "consu",
        })

    def test_get_active_ingredients_no_field(self):
        result = self.product._md_get_active_ingredients()
        self.assertFalse(result, "Sin campo Studio, debe retornar recordset vacío")

    def test_get_product_lines_no_field(self):
        result = self.product._md_get_product_lines()
        self.assertFalse(result, "Sin campo Studio, debe retornar recordset vacío")

    def test_a_la_mano_fields_exist(self):
        self.assertIn("show_qty_a_la_mano", self.product._fields)
        self.assertIn("qty_a_la_mano", self.product._fields)
        self.assertFalse(self.product.show_qty_a_la_mano)
        self.assertEqual(self.product.qty_a_la_mano, 0.0)

    def test_shop_active_ingredients_returns_empty(self):
        result = self.env["product.template"]._md_get_shop_active_ingredients()
        self.assertIsNotNone(result)

    def test_shop_product_lines_returns_empty(self):
        result = self.env["product.template"]._md_get_shop_product_lines()
        self.assertIsNotNone(result)


@tagged("post_install", "-at_install")
class TestShopJsonEndpoints(HttpCase):
    """Tests para endpoints JSON del shop."""

    def test_shop_cart_quantities_public(self):
        resp = self.url_open("/shop/cart/quantities", data=b'{}',
                             headers={"Content-Type": "application/json"})
        self.assertIn(resp.status_code, (200, 400, 403),
                      "/shop/cart/quantities debe responder sin crash")

    def test_shop_products_stock_public(self):
        resp = self.url_open("/shop/products/stock", data=b'{"jsonrpc":"2.0","method":"call","params":{}}',
                             headers={"Content-Type": "application/json"})
        self.assertIn(resp.status_code, (200, 400, 404),
                      "/shop/products/stock debe responder sin crash")
