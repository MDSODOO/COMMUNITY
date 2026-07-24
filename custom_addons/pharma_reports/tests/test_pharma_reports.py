# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPharmaReports(TransactionCase):
    """
    Verifica que los reportes farmacéuticos estén correctamente registrados.

    Regla de negocio: las cantidades de inventario físico se etiquetan
    "A la mano" — no "Disponible", "Stock" ni "Existencias".
    """

    def test_sale_order_report_action_exists(self):
        """El reporte de Orden de Venta debe estar registrado."""
        action = self.env['ir.actions.report'].search([
            ('model', '=', 'sale.order'),
            ('report_name', 'ilike', 'pharma'),
        ], limit=1)
        self.assertTrue(
            action,
            "No se encontró acción de reporte pharma para sale.order",
        )

    def test_purchase_order_report_action_exists(self):
        """El reporte de Orden de Compra debe estar registrado."""
        action = self.env['ir.actions.report'].search([
            ('model', '=', 'purchase.order'),
            ('report_name', 'ilike', 'pharma'),
        ], limit=1)
        self.assertTrue(
            action,
            "No se encontró acción de reporte pharma para purchase.order",
        )

    def test_stock_picking_transfer_report_exists(self):
        """El reporte de Transferencias debe estar registrado."""
        action = self.env['ir.actions.report'].search([
            ('model', '=', 'stock.picking'),
            ('report_name', 'ilike', 'transferencias'),
        ], limit=1)
        self.assertTrue(
            action,
            "No se encontró acción de reporte de transferencias para stock.picking",
        )

    def test_sale_paperformat_exists(self):
        """El paperformat de ventas pharma debe existir en la BD."""
        pf = self.env['report.paperformat'].search([
            ('name', 'ilike', 'Medicine Depot'),
            ('name', 'ilike', 'Ventas'),
        ], limit=1)
        self.assertTrue(pf, "Paperformat de ventas Medicine Depot no encontrado")

    def test_purchase_paperformat_exists(self):
        """El paperformat de compras pharma debe existir en la BD."""
        pf = self.env['report.paperformat'].search([
            ('name', 'ilike', 'Medicine Depot'),
            ('name', 'ilike', 'Compras'),
        ], limit=1)
        self.assertTrue(pf, "Paperformat de compras Medicine Depot no encontrado")

    def test_sale_report_layout_template_exists(self):
        """El template QWeb de OV debe estar registrado como ir.ui.view."""
        view = self.env['ir.ui.view'].search([
            ('key', 'ilike', 'pharma_reports'),
            ('type', '=', 'qweb'),
        ], limit=1)
        self.assertTrue(view, "No hay vistas QWeb registradas para pharma_reports")

    def test_no_disponible_in_report_names(self):
        """
        Ninguna acción de reporte del módulo debe contener 'Disponible'
        en su nombre — regla terminológica: siempre 'A la mano'.
        """
        actions = self.env['ir.actions.report'].search([
            ('report_name', 'ilike', 'pharma'),
        ])
        for action in actions:
            self.assertNotIn(
                'disponible', (action.name or '').lower(),
                f"Reporte '{action.name}' usa 'disponible' — debe decir 'A la mano'",
            )

    def test_physical_inventory_report_action_exists(self):
        """El reporte de Ajuste de Inventario Físico debe estar registrado."""
        action = self.env['ir.actions.report'].search([
            ('model', '=', 'stock.quant'),
            ('report_name', '=', 'pharma_reports.report_physical_inventory_document'),
        ], limit=1)
        self.assertTrue(
            action,
            "No se encontró la acción del reporte pharma para stock.quant (Inventario Físico)",
        )

    def test_physical_inventory_view_pharma_inherit_exists(self):
        """La vista de herencia de stock.quant para inventario físico debe existir."""
        view = self.env['ir.ui.view'].search([
            ('model', '=', 'stock.quant'),
            ('name', '=', 'stock.quant.inventory.list.pharma.inherit'),
        ], limit=1)
        self.assertTrue(
            view,
            "No se encontró la vista heredada de inventario físico stock.quant.inventory.list.pharma.inherit",
        )

    def test_physical_inventory_excel_action_exists(self):
        """La exportación Excel de inventario físico debe estar registrada."""
        action = self.env['ir.actions.server'].search([
            ('model_id.model', '=', 'stock.quant'),
            ('name', '=', 'Exportar Inventario Físico a Excel'),
        ], limit=1)
        self.assertTrue(
            action,
            "No se encontró la acción Excel para Inventario Físico",
        )
