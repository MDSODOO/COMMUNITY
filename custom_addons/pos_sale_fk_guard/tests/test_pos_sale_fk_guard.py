# -*- coding: utf-8 -*-
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPosSaleFkGuard(TransactionCase):
    """
    Tests del guardián de FK entre POS y sale.order.line.

    Verifica que _sanitize_sale_fk_references nullifique referencias
    obsoletas antes de que el ORM intente la inserción en BD.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.PosOrder = cls.env['pos.order']
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente POS Test'})
        cls.product = cls.env['product.product'].create({
            'name': 'Producto POS Test',
            'type': 'consu',
            'available_in_pos': True,
        })

    def _make_order_payload(self, sale_order_line_id=None, sale_order_origin_id=None):
        """Construye un payload mínimo de POS con los FK indicados."""
        line_vals = {
            'product_id': self.product.id,
            'qty': 1,
            'price_unit': 100.0,
        }
        if sale_order_line_id is not None:
            line_vals['sale_order_line_id'] = sale_order_line_id
        if sale_order_origin_id is not None:
            line_vals['sale_order_origin_id'] = sale_order_origin_id

        return {
            'name': 'POS-TEST-001',
            'lines': [
                [Command.CREATE, 0, line_vals],
            ],
        }

    # ------------------------------------------------------------------ #
    # Caso 1: sin FK → no hay cambios                                     #
    # ------------------------------------------------------------------ #

    def test_no_fk_no_change(self):
        """Payload sin FKs de venta no debe ser modificado."""
        payload = self._make_order_payload()
        original_vals = dict(payload['lines'][0][2])
        self.PosOrder._sanitize_sale_fk_references(payload)
        self.assertEqual(payload['lines'][0][2], original_vals)

    # ------------------------------------------------------------------ #
    # Caso 2: FK válida → no se nullifica                                 #
    # ------------------------------------------------------------------ #

    def test_valid_sale_order_line_id_preserved(self):
        """FK a una línea de OV existente no debe modificarse."""
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100,
            })],
        })
        valid_line_id = so.order_line[0].id
        payload = self._make_order_payload(sale_order_line_id=valid_line_id)
        self.PosOrder._sanitize_sale_fk_references(payload)
        self.assertEqual(
            payload['lines'][0][2]['sale_order_line_id'],
            valid_line_id,
            "FK válida no debe ser nullificada",
        )

    # ------------------------------------------------------------------ #
    # Caso 3: FK obsoleta → se nullifica                                  #
    # ------------------------------------------------------------------ #

    def test_stale_sale_order_line_id_nullified(self):
        """FK a una línea de OV que no existe → debe quedar en False."""
        non_existent_id = 999999999
        payload = self._make_order_payload(sale_order_line_id=non_existent_id)
        self.PosOrder._sanitize_sale_fk_references(payload)
        self.assertFalse(
            payload['lines'][0][2]['sale_order_line_id'],
            "FK obsoleta debe quedar en False para evitar IntegrityError",
        )

    def test_stale_sale_order_origin_id_nullified(self):
        """FK obsoleta de sale_order_origin_id también debe nullificarse."""
        payload = self._make_order_payload(sale_order_origin_id=999999999)
        self.PosOrder._sanitize_sale_fk_references(payload)
        self.assertFalse(
            payload['lines'][0][2]['sale_order_origin_id'],
            "sale_order_origin_id obsoleto debe quedar en False",
        )

    # ------------------------------------------------------------------ #
    # Caso 4: múltiples líneas — solo la inválida se nullifica            #
    # ------------------------------------------------------------------ #

    def test_only_stale_line_nullified(self):
        """Con dos líneas, solo la obsoleta debe modificarse."""
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100,
            })],
        })
        valid_id = so.order_line[0].id
        payload = {
            'name': 'POS-TEST-002',
            'lines': [
                [Command.CREATE, 0, {'product_id': self.product.id, 'sale_order_line_id': valid_id}],
                [Command.CREATE, 0, {'product_id': self.product.id, 'sale_order_line_id': 999999999}],
            ],
        }
        self.PosOrder._sanitize_sale_fk_references(payload)
        self.assertEqual(payload['lines'][0][2]['sale_order_line_id'], valid_id)
        self.assertFalse(payload['lines'][1][2]['sale_order_line_id'])

    # ------------------------------------------------------------------ #
    # Caso 5: payload vacío o sin líneas → no lanza excepción             #
    # ------------------------------------------------------------------ #

    def test_empty_payload_no_crash(self):
        payload = {}
        self.PosOrder._sanitize_sale_fk_references(payload)  # no debe lanzar

    def test_empty_lines_no_crash(self):
        payload = {'name': 'X', 'lines': []}
        self.PosOrder._sanitize_sale_fk_references(payload)  # no debe lanzar
