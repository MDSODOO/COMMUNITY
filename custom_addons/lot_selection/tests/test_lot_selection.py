# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestLotSelectionDomain(TransactionCase):
    """
    Tests del motor FEFO de lot_selection.
    Regla de negocio: inventario físico = "A la mano".
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.product = cls.env['product.product'].create({
            'name': 'Medicamento Test',
            'type': 'consu',
            'tracking': 'lot',
            'use_expiration_date': True,
        })
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1
        )
        cls.partner = cls.env['res.partner'].create({'name': 'Farmacia Test'})

        today = fields.Datetime.now()
        cls.lot_near = cls.env['stock.lot'].create({
            'name': 'LOTE-CERCA',
            'product_id': cls.product.id,
            'company_id': cls.env.company.id,
            'expiration_date': today + timedelta(days=30),
        })
        cls.lot_far = cls.env['stock.lot'].create({
            'name': 'LOTE-LEJOS',
            'product_id': cls.product.id,
            'company_id': cls.env.company.id,
            'expiration_date': today + timedelta(days=180),
        })
        # Poner A la mano en el almacén
        for lot in (cls.lot_near, cls.lot_far):
            cls.env['stock.quant']._update_available_quantity(
                cls.product,
                cls.warehouse.lot_stock_id,
                quantity=10.0,
                lot_id=lot,
            )

    def _make_sale_order(self):
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'warehouse_id': self.warehouse.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100,
            })],
        })

    def test_lot_domain_includes_lots_with_stock(self):
        """El dominio debe incluir lotes con cantidad A la mano > 0."""
        so = self._make_sale_order()
        line = so.order_line[0]
        line._compute_lot_domain()
        domain = line.lot_domain
        self.assertNotEqual(
            domain, [('id', '=', 0)],
            "El dominio no debe estar vacío cuando hay lotes A la mano",
        )

    def test_lot_domain_empty_for_untracked_product(self):
        """Productos sin seguimiento → dominio vacío (no aplica FEFO)."""
        product_no_tracking = self.env['product.product'].create({
            'name': 'Producto Sin Lote',
            'type': 'consu',
            'tracking': 'none',
        })
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'warehouse_id': self.warehouse.id,
            'order_line': [(0, 0, {
                'product_id': product_no_tracking.id,
                'product_uom_qty': 1,
                'price_unit': 50,
            })],
        })
        line = so.order_line[0]
        line._compute_lot_domain()
        self.assertEqual(line.lot_domain, [('id', '=', 0)])

    def test_onchange_auto_selects_fefo_lot(self):
        """Al hacer onchange, debe seleccionarse el lote con caducidad más próxima."""
        so = self._make_sale_order()
        line = so.order_line[0]
        line._onchange_product_set_lot()
        if line.lot_id:
            self.assertEqual(
                line.lot_id, self.lot_near,
                "FEFO debe seleccionar el lote con caducidad más próxima",
            )

    def test_sale_confirm_propagates_lot_to_move_lines(self):
        """Confirmar la OV propaga el lot_id a las líneas de movimiento."""
        so = self._make_sale_order()
        line = so.order_line[0]
        line.lot_id = self.lot_near
        so.action_confirm()

        move_lines_with_lot = so.picking_ids.mapped('move_line_ids').filtered(
            lambda ml: ml.lot_id == self.lot_near
        )
        self.assertTrue(
            move_lines_with_lot,
            "El lote seleccionado debe propagarse a las move_lines al confirmar",
        )


@tagged('post_install', '-at_install')
class TestLotSelectionPurchase(TransactionCase):
    """Tests de validación de caducidad en órdenes de compra."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.product = cls.env['product.product'].create({
            'name': 'Medicamento Compra Test',
            'type': 'consu',
            'tracking': 'lot',
            'use_expiration_date': True,
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Proveedor Test',
            'supplier_rank': 1,
        })
        cls.env['product.supplierinfo'].create({
            'partner_id': cls.partner.id,
            'product_tmpl_id': cls.product.product_tmpl_id.id,
            'price': 10.0,
        })

    def _make_purchase_order(self, lot_expiration_date=None):
        lot = self.env['stock.lot'].create({
            'name': 'LOT-PO-TEST',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        po = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 5,
                'price_unit': 10,
                'lot_id': lot.id,
                'lot_expiration_date': lot_expiration_date,
                'date_planned': fields.Datetime.now(),
            })],
        })
        return po, lot

    def test_confirm_raises_if_lot_expired(self):
        """Confirmar OC con lote vencido debe lanzar UserError."""
        past_date = fields.Datetime.now() - timedelta(days=1)
        po, _ = self._make_purchase_order(lot_expiration_date=past_date)
        with self.assertRaises(UserError):
            po.action_confirm()

    def test_confirm_raises_if_no_expiration_date(self):
        """Confirmar OC con lote sin fecha de caducidad debe lanzar UserError."""
        po, _ = self._make_purchase_order(lot_expiration_date=None)
        with self.assertRaises(UserError):
            po.action_confirm()

    def test_sync_expiration_date_to_lot(self):
        """La fecha en la línea de OC debe sincronizarse al stock.lot."""
        future_date = fields.Datetime.now() + timedelta(days=90)
        po, lot = self._make_purchase_order(lot_expiration_date=future_date)
        line = po.order_line[0]
        line._sync_lot_expiration_to_stock_lot()
        self.assertEqual(lot.expiration_date, future_date)
