from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestSaleStockAvailabilityDomain(TransactionCase):
    """Test que el catálogo filtra productos sin stock"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_order = cls.env["sale.order"]
        cls.product = cls.env["product.product"]
        cls.stock_move = cls.env["stock.move"]
        cls.stock_location = cls.env["stock.location"]

        cls.customer = cls.env["res.partner"].create({
            "name": "Test Customer",
            "customer_rank": 1,
        })

        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.stock_loc = cls.warehouse.lot_stock_id

        cls.product_with_stock = cls.product.create({
            "name": "Product With Stock",
            "type": "product",
            "tracking": "none",
        })
        cls.product_without_stock = cls.product.create({
            "name": "Product Without Stock",
            "type": "product",
            "tracking": "none",
        })
        cls.product_service = cls.product.create({
            "name": "Service Product",
            "type": "service",
        })

        cls._set_inventory(cls.product_with_stock, 100)
        # product_without_stock stays at 0

    def _set_inventory(self, product, qty):
        self.env["stock.quant"]._update_available_quantity(
            product, self.stock_loc, qty
        )

    def test_01_catalog_domain_filters_no_stock(self):
        """Catálogo debe ocultar productos sin stock (is_storable=True)"""
        order = self.sale_order.create({
            "partner_id": self.customer.id,
            "order_line": [],
        })

        domain = order._get_product_catalog_domain()

        # Productos con stock deben estar en el dominio
        product_with_stock_match = self.product_with_stock.search(domain)
        self.assertIn(self.product_with_stock, product_with_stock_match)

        # Productos sin stock NO deben estar
        product_without_stock_match = self.product_without_stock.search(domain)
        self.assertNotIn(self.product_without_stock, product_without_stock_match)

        # Servicios sí (no son almacenables, bypass del domain)
        product_service_match = self.product_service.search(domain)
        self.assertIn(self.product_service, product_service_match)

    def test_02_catalog_domain_respects_parent(self):
        """Domain debe combinar correctamente con el domain padre"""
        order = self.sale_order.create({
            "partner_id": self.customer.id,
        })

        domain = order._get_product_catalog_domain()

        # Debe ser una cadena AND que respeta both constraints
        product_qs = self.product.search(domain)
        for p in product_qs:
            if p.is_storable:
                self.assertGreater(p.qty_available, 0,
                    f"Product {p.name} en catálogo tiene qty_available={p.qty_available}")


class TestSaleOrderLineQuantityEnforcement(TransactionCase):
    """Test que la cantidad se limita al A la mano en todos los puntos"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_order = cls.env["sale.order"]
        cls.sale_order_line = cls.env["sale.order.line"]
        cls.product = cls.env["product.product"]

        cls.customer = cls.env["res.partner"].create({
            "name": "Test Customer",
            "customer_rank": 1,
        })

        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.stock_loc = cls.warehouse.lot_stock_id

        cls.product_test = cls.product.create({
            "name": "Product Test",
            "type": "product",
            "tracking": "none",
        })
        cls._set_inventory(cls.product_test, 50)

        cls.order = cls.sale_order.create({
            "partner_id": cls.customer.id,
        })

    def _set_inventory(self, product, qty):
        self.env["stock.quant"]._update_available_quantity(
            product, self.stock_loc, qty
        )

    def test_03_create_clamps_qty(self):
        """create() debe clampar product_uom_qty al A la mano"""
        line = self.sale_order_line.create({
            "order_id": self.order.id,
            "product_id": self.product_test.id,
            "product_uom_qty": 100,  # > qty_available (50)
            "product_uom_id": self.product_test.uom_id.id,
        })

        self.assertEqual(line.product_uom_qty, 50,
            "create() debe clampar a A la mano")

    def test_04_write_clamps_qty(self):
        """write() debe clampar product_uom_qty al A la mano"""
        line = self.sale_order_line.create({
            "order_id": self.order.id,
            "product_id": self.product_test.id,
            "product_uom_qty": 30,
            "product_uom_id": self.product_test.uom_id.id,
        })

        line.write({"product_uom_qty": 100})
        self.assertEqual(line.product_uom_qty, 50,
            "write() debe clampar a A la mano")

    def test_05_constraint_as_safety_net(self):
        """Constraint debe levantarse como red de seguridad final"""
        # Crear línea con stock suficiente
        line = self.sale_order_line.create({
            "order_id": self.order.id,
            "product_id": self.product_test.id,
            "product_uom_qty": 30,
        })

        # Reducir stock por debajo de cantidad en línea
        self._set_inventory(self.product_test, 10)

        # Intentar cambiar producto fuerza constraint check
        with self.assertRaises(ValidationError) as cm:
            line.write({
                "product_id": self.product_test.id,
                "product_uom_qty": 30,
            })
        self.assertIn("A la mano", str(cm.exception))

    def test_06_create_multi_clamps_all(self):
        """create() con múltiples líneas debe clampar todas"""
        lines = self.sale_order_line.create([
            {
                "order_id": self.order.id,
                "product_id": self.product_test.id,
                "product_uom_qty": 100,
            },
            {
                "order_id": self.order.id,
                "product_id": self.product_test.id,
                "product_uom_qty": 80,
            },
        ])

        for line in lines:
            self.assertEqual(line.product_uom_qty, 50,
                "create_multi debe clampar cada línea")

    def test_07_no_clamp_non_storable(self):
        """Productos no almacenables no deben ser clampados"""
        service = self.env["product.product"].create({
            "name": "Service",
            "type": "service",
        })

        line = self.sale_order_line.create({
            "order_id": self.order.id,
            "product_id": service.id,
            "product_uom_qty": 9999,
        })

        self.assertEqual(line.product_uom_qty, 9999,
            "Servicios no deben ser clampados")

    def test_08_no_clamp_display_type(self):
        """Líneas con display_type no deben ser clampadas"""
        line = self.sale_order_line.create({
            "order_id": self.order.id,
            "display_type": "line_section",
            "product_uom_qty": 9999,
        })

        self.assertEqual(line.product_uom_qty, 9999,
            "display_type lines no deben ser clampadas")

    def test_09_no_clamp_confirmed_states(self):
        """Estados sale/done/cancel no deben ser clampados"""
        line = self.sale_order_line.create({
            "order_id": self.order.id,
            "product_id": self.product_test.id,
            "product_uom_qty": 30,
        })

        # Confirmar orden
        self.order.action_confirm()
        self.assertEqual(self.order.state, "sale")

        # Intentar escribir cantidad > stock en estado confirmado
        line.write({"product_uom_qty": 100})
        self.assertEqual(line.product_uom_qty, 100,
            "Estados confirmados no deben ser clampados")


class TestSaleOrderLineUOMConversion(TransactionCase):
    """Test que conversiones de UOM funcionen correctamente"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_order = cls.env["sale.order"]
        cls.sale_order_line = cls.env["sale.order.line"]
        cls.product = cls.env["product.product"]
        cls.uom = cls.env["uom.uom"]

        cls.customer = cls.env["res.partner"].create({
            "name": "Test Customer",
            "customer_rank": 1,
        })

        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.stock_loc = cls.warehouse.lot_stock_id

        # Crear UOM: Kilogramos (base)
        cls.kg_uom = cls.uom.create({
            "name": "Kilogram",
            "category_id": cls.env.ref("uom.product_uom_categ_kgm").id,
            "uom_type": "reference",
            "ratio": 1.0,
        })

        # Crear UOM: Gramos (derivada de kg)
        cls.g_uom = cls.uom.create({
            "name": "Gram",
            "category_id": cls.kg_uom.category_id.id,
            "uom_type": "smaller",
            "factor": 1000.0,  # 1 kg = 1000 g
        })

        # Producto con UOM kg
        cls.product_kg = cls.product.create({
            "name": "Product in KG",
            "type": "product",
            "uom_id": cls.kg_uom.id,
            "uom_po_id": cls.kg_uom.id,
        })
        cls._set_inventory(cls.product_kg, 10)  # 10 kg = 10000 g

        cls.order = cls.sale_order.create({
            "partner_id": cls.customer.id,
        })

    def _set_inventory(self, product, qty):
        self.env["stock.quant"]._update_available_quantity(
            product, self.stock_loc, qty
        )

    def test_10_uom_conversion_clamping(self):
        """Clamping debe respetar conversión de UOM"""
        # Intentar pedir 15000 gramos (15 kg) cuando hay 10 kg
        line = self.sale_order_line.create({
            "order_id": self.order.id,
            "product_id": self.product_kg.id,
            "product_uom_id": self.g_uom.id,  # Solicitar en gramos
            "product_uom_qty": 15000,  # 15 kg en gramos
        })

        # Debe clampear a 10000 gramos (10 kg)
        self.assertEqual(line.product_uom_qty, 10000,
            "Clamping debe convertir correctamente entre UOM")

    def test_11_uom_conversion_within_limits(self):
        """Cantidades dentro del límite no deben ser tocadas"""
        line = self.sale_order_line.create({
            "order_id": self.order.id,
            "product_id": self.product_kg.id,
            "product_uom_id": self.g_uom.id,
            "product_uom_qty": 8000,  # 8 kg en gramos (< 10 kg)
        })

        self.assertEqual(line.product_uom_qty, 8000,
            "Cantidades dentro del límite no deben cambiar")


class TestUpdateOrderLineInfo(TransactionCase):
    """Test que _update_order_line_info (catálogo) clampee correctamente"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_order = cls.env["sale.order"]
        cls.product = cls.env["product.product"]

        cls.customer = cls.env["res.partner"].create({
            "name": "Test Customer",
            "customer_rank": 1,
        })

        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.stock_loc = cls.warehouse.lot_stock_id

        cls.product_test = cls.product.create({
            "name": "Product Test",
            "type": "product",
        })
        cls._set_inventory(cls.product_test, 50)

        cls.order = cls.sale_order.create({
            "partner_id": cls.customer.id,
        })

    def _set_inventory(self, product, qty):
        self.env["stock.quant"]._update_available_quantity(
            product, self.stock_loc, qty
        )

    def test_12_update_order_line_info_clamps(self):
        """_update_order_line_info debe clampar cantidad del catálogo"""
        result = self.order._update_order_line_info(
            self.product_test.id,
            quantity=100,  # > qty_available (50)
        )

        # La cantidad retornada debe estar clampeada
        self.assertEqual(result["product_uom_qty"], 50,
            "_update_order_line_info debe clampar al stock")

    def test_13_update_order_line_info_no_clamp_service(self):
        """_update_order_line_info no debe clampar servicios"""
        service = self.env["product.product"].create({
            "name": "Service",
            "type": "service",
        })

        result = self.order._update_order_line_info(
            service.id,
            quantity=9999,
        )

        self.assertEqual(result["product_uom_qty"], 9999,
            "_update_order_line_info no debe clampar servicios")


class TestMaxQtyInLineUOM(TransactionCase):
    """Test helpers para cálculo de cantidad máxima"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_order = cls.env["sale.order"]
        cls.sale_order_line = cls.env["sale.order.line"]
        cls.product = cls.env["product.product"]
        cls.uom = cls.env["uom.uom"]

        cls.customer = cls.env["res.partner"].create({
            "name": "Test Customer",
            "customer_rank": 1,
        })

        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.stock_loc = cls.warehouse.lot_stock_id

        cls.kg_uom = cls.uom.create({
            "name": "Kilogram",
            "category_id": cls.env.ref("uom.product_uom_categ_kgm").id,
            "uom_type": "reference",
            "ratio": 1.0,
        })

        cls.g_uom = cls.uom.create({
            "name": "Gram",
            "category_id": cls.kg_uom.category_id.id,
            "uom_type": "smaller",
            "factor": 1000.0,
        })

        cls.product_kg = cls.product.create({
            "name": "Product in KG",
            "type": "product",
            "uom_id": cls.kg_uom.id,
        })
        cls._set_inventory(cls.product_kg, 10)

        cls.order = cls.sale_order.create({
            "partner_id": cls.customer.id,
        })

        cls.line = cls.sale_order_line.create({
            "order_id": cls.order.id,
            "product_id": cls.product_kg.id,
            "product_uom_id": cls.g_uom.id,
            "product_uom_qty": 5000,
        })

    def _set_inventory(self, product, qty):
        self.env["stock.quant"]._update_available_quantity(
            product, self.stock_loc, qty
        )

    def test_14_max_qty_in_line_uom_conversion(self):
        """_max_qty_in_line_uom debe convertir correctamente"""
        max_qty = self.line._max_qty_in_line_uom()
        # 10 kg en product.uom_id convertido a gramos = 10000
        self.assertEqual(max_qty, 10000,
            "_max_qty_in_line_uom debe retornar cantidad en line UOM")

    def test_15_exceeds_available_stock(self):
        """_exceeds_available_stock debe detectar overstock"""
        self.assertTrue(
            self.line._exceeds_available_stock() is False,
            "Línea con 5000g < 10kg debe estar ok"
        )

        self.line.product_uom_qty = 15000
        self.assertTrue(
            self.line._exceeds_available_stock(),
            "Línea con 15000g > 10kg debe exceder stock"
        )


class TestOnchangeWarning(TransactionCase):
    """Test que onchange emita warning y auto-corrija"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_order = cls.env["sale.order"]
        cls.sale_order_line = cls.env["sale.order.line"]
        cls.product = cls.env["product.product"]

        cls.customer = cls.env["res.partner"].create({
            "name": "Test Customer",
            "customer_rank": 1,
        })

        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.stock_loc = cls.warehouse.lot_stock_id

        cls.product_test = cls.product.create({
            "name": "Product Test",
            "type": "product",
        })
        cls._set_inventory(cls.product_test, 50)

        cls.order = cls.sale_order.create({
            "partner_id": cls.customer.id,
        })

    def _set_inventory(self, product, qty):
        self.env["stock.quant"]._update_available_quantity(
            product, self.stock_loc, qty
        )

    def test_16_onchange_warns_and_clamps(self):
        """onchange debe avisar y ajustar cantidad"""
        line = self.sale_order_line.create({
            "order_id": self.order.id,
            "product_id": self.product_test.id,
            "product_uom_qty": 30,
        })

        line.product_uom_qty = 100

        result = line._onchange_warn_qty_available()

        # Debe retornar warning
        self.assertIsNotNone(result)
        self.assertIn("warning", result)
        self.assertIn("Stock insuficiente", result["warning"]["title"])

        # Debe haber ajustado la cantidad
        self.assertEqual(line.product_uom_qty, 50,
            "onchange debe ajustar cantidad al A la mano")
