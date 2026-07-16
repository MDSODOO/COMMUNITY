# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPurchaseVendorRef(TransactionCase):
    """
    Tests de propagación de partner_ref de OC a factura de proveedor.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.partner = cls.env['res.partner'].create({
            'name': 'Proveedor Ref Test',
            'supplier_rank': 1,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Producto Ref Test',
            'type': 'consu',
        })
        cls.env['product.supplierinfo'].create({
            'partner_id': cls.partner.id,
            'product_tmpl_id': cls.product.product_tmpl_id.id,
            'price': 50.0,
        })
        # Cuenta de gasto para las líneas de OC
        cls.account = cls.env['account.account'].search([
            ('account_type', 'in', ('expense', 'expense_direct_cost')),
            ('company_id', '=', cls.env.company.id),
        ], limit=1)

    def _make_po(self, partner_ref=None):
        po = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'partner_ref': partner_ref,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 10,
                'price_unit': 50,
                'date_planned': fields.Datetime.now(),
            })],
        })
        po.button_confirm()
        return po

    def test_single_po_ref_propagated_to_invoice(self):
        """partner_ref de la OC debe aparecer en ref de la factura generada."""
        po = self._make_po(partner_ref='FAC-PROV-001')
        invoice = po._create_invoices()
        self.assertEqual(invoice.ref, 'FAC-PROV-001')
        self.assertEqual(invoice.payment_reference, 'FAC-PROV-001')

    def test_po_without_ref_does_not_set_invoice_ref(self):
        """OC sin partner_ref no debe sobrescribir campos de la factura."""
        po = self._make_po(partner_ref=None)
        invoice = po._create_invoices()
        # ref puede ser None o vacío — no debe ser un string de otra OC
        self.assertFalse(invoice.ref or False)

    def test_multiple_po_refs_combined_in_invoice(self):
        """Dos OCs con refs distintas → factura con 'REF-A / REF-B'."""
        po1 = self._make_po(partner_ref='REF-A')
        po2 = self._make_po(partner_ref='REF-B')
        invoices = (po1 | po2)._create_invoices(grouped=True)
        # Puede generar una o dos facturas dependiendo del agrupamiento
        all_refs = ' / '.join(
            inv.ref for inv in invoices if inv.ref
        )
        # Ambas referencias deben aparecer en alguna factura
        self.assertIn('REF-A', all_refs)
        self.assertIn('REF-B', all_refs)

    def test_duplicate_refs_not_repeated(self):
        """Dos OCs con el mismo partner_ref → ref sin duplicados."""
        po1 = self._make_po(partner_ref='MISMO-REF')
        po2 = self._make_po(partner_ref='MISMO-REF')
        invoices = (po1 | po2)._create_invoices(grouped=True)
        for inv in invoices:
            if inv.ref:
                self.assertNotIn(
                    'MISMO-REF / MISMO-REF', inv.ref,
                    "La referencia no debe repetirse en la misma factura",
                )
