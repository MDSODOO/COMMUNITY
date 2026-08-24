# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductCostHistory(models.Model):
    _name = 'product.cost.history'
    _description = 'Historial de costos de compra'
    _order = 'date desc, id desc'
    _rec_name = 'reference'
    _check_company_auto = True

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Producto',
        required=True,
        index=True,
        ondelete='cascade',
        check_company=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Variante',
        required=True,
        index=True,
        ondelete='restrict',
        check_company=True,
    )
    date = fields.Datetime(
        string='Fecha de entrada',
        required=True,
        index=True,
    )
    cost = fields.Monetary(
        string='Costo facturado',
        currency_field='currency_id',
        required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        required=True,
    )
    reference = fields.Char(
        string='Referencia',
        required=True,
    )
    account_move_id = fields.Many2one(
        'account.move',
        string='Factura',
        required=True,
        index=True,
        ondelete='cascade',
        check_company=True,
    )
    account_move_line_id = fields.Many2one(
        'account.move.line',
        string='Linea de factura',
        required=True,
        index=True,
        ondelete='cascade',
        check_company=True,
    )
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Orden de compra',
        index=True,
        ondelete='set null',
        check_company=True,
    )
    purchase_line_id = fields.Many2one(
        'purchase.order.line',
        string='Linea de compra',
        index=True,
        ondelete='set null',
        check_company=True,
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Recepcion',
        index=True,
        ondelete='set null',
        check_company=True,
    )
    stock_move_id = fields.Many2one(
        'stock.move',
        string='Movimiento de entrada',
        index=True,
        ondelete='set null',
        check_company=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )

    _account_move_line_unique = models.Constraint(
        'unique(account_move_line_id)',
        'Ya existe un historial de costo para esta linea de factura.',
    )
