from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestInvoiceParserHardStops(TransactionCase):
    """
    Hard Stops: bloquear la creación de la Orden de Compra cuando el CFDI
    trae una discrepancia de IVA respecto al impuesto de proveedor
    configurado en el producto, o cuando falta un lote válido para un
    producto con seguimiento por lote ('A la Mano' / On Hand).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Proveedor Hard Stop Test",
            "supplier_rank": 1,
            "vat": "AAA010101AA1",
        })

        cls.tax_16 = cls.env["account.tax"].search([
            ("type_tax_use", "=", "purchase"),
            ("company_id", "=", cls.env.company.id),
            ("amount_type", "=", "percent"),
            ("amount", "=", 16.0),
        ], limit=1)
        if not cls.tax_16:
            cls.tax_16 = cls.env["account.tax"].create({
                "name": "IVA Compras 16 Hard Stop Test",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 16.0,
            })

        # Producto con IVA de compra configurado en 16% — usado en test_block_invalid_iva.
        cls.product_iva = cls.env["product.product"].create({
            "name": "Paracetamol 500mg",
            "type": "product",
            "purchase_ok": True,
            "tracking": "none",
            "barcode": "7500000000001",
            "supplier_taxes_id": [(6, 0, cls.tax_16.ids)],
        })

        # Producto trazado por lote — usado en test_block_missing_lot.
        cls.product_lot = cls.env["product.product"].create({
            "name": "Amoxicilina 500mg",
            "type": "product",
            "purchase_ok": True,
            "tracking": "lot",
            "barcode": "7500000000002",
        })

    def _wizard(self, line_vals, folio="HARD-STOP-TEST"):
        return self.env["purchase.invoice.import.wizard"].create({
            "partner_id": self.partner.id,
            "cfdi_folio": folio,
            "state": "review",
            "line_ids": [(0, 0, line_vals)],
        })

    def test_block_invalid_iva(self):
        """
        Producto configurado con IVA de compra 16% en Odoo, pero el CFDI
        trae una TasaOCuota de 8% (Tasa, no Exento) -> discrepancia real de
        tasas distintas de cero. Debe bloquear con ValidationError.
        """
        wizard = self._wizard({
            "no_identificacion": "7500000000001",
            "descripcion": self.product_iva.display_name,
            "product_id": self.product_iva.id,
            "cantidad": 10,
            "valor_unitario": 25.0,
            "tasa_iva": 0.08,
            "factor_iva": "Tasa",
            "iva_presente": True,
        }, folio="HARD-STOP-IVA")

        with self.assertRaises(ValidationError) as ctx:
            wizard.action_create_purchase_order()

        message = str(ctx.exception)
        self.assertIn("Discrepancia de IVA", message)
        self.assertIn("Paracetamol 500mg", message)
        self.assertFalse(
            self.env["purchase.order"].search([("partner_ref", "=", "HARD-STOP-IVA")]),
            "No debe haberse creado ninguna OC cuando la validación de IVA falla.",
        )

    def test_allows_exento_cfdi_even_if_product_has_configured_tax(self):
        """
        Excepción intencional: un CFDI que declara explícitamente 0%/Exento
        para un producto configurado con 16% de compra NO debe bloquearse
        (una factura puntual puede llegar legítimamente sin IVA). Ver
        docs/audits — este caso ya estaba cubierto antes del Hard Stop y
        debe seguir permitido.
        """
        wizard = self._wizard({
            "no_identificacion": "7500000000001",
            "descripcion": self.product_iva.display_name,
            "product_id": self.product_iva.id,
            "cantidad": 10,
            "valor_unitario": 25.0,
            "tasa_iva": 0.0,
            "factor_iva": "Exento",
            "iva_presente": True,
        }, folio="HARD-STOP-IVA-EXENTO-OK")

        action = wizard.action_create_purchase_order()
        order = self.env["purchase.order"].browse(action["res_id"])
        self.assertFalse(order.order_line.tax_ids)

    def test_block_missing_lot(self):
        """
        Producto con tracking='lot' sin ningún lote resuelto desde el
        CFDI/PDF (line.lot_ids vacío) -> debe bloquear con ValidationError
        mencionando 'A la Mano' (On Hand).
        """
        wizard = self._wizard({
            "no_identificacion": "7500000000002",
            "descripcion": self.product_lot.display_name,
            "product_id": self.product_lot.id,
            "cantidad": 5,
            "valor_unitario": 40.0,
            "tasa_iva": 0.0,
            "iva_presente": False,
        }, folio="HARD-STOP-LOT")

        with self.assertRaises(ValidationError) as ctx:
            wizard.action_create_purchase_order()

        message = str(ctx.exception)
        self.assertIn("Lote", message)
        self.assertIn("A la Mano", message)
        self.assertFalse(
            self.env["purchase.order"].search([("partner_ref", "=", "HARD-STOP-LOT")]),
            "No debe haberse creado ninguna OC cuando falta el lote.",
        )
