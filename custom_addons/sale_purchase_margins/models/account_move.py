# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import fields, models

from .margin_tools import convert_unit_price


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        self._qfm_create_purchase_cost_history()
        return res

    def _qfm_create_purchase_cost_history(self):
        bills = self.filtered(
            lambda move: move.move_type == 'in_invoice' and move.state == 'posted'
        )
        if not bills:
            return

        History = self.env['product.cost.history'].sudo()
        for bill in bills:
            for line in bill.invoice_line_ids.filtered(
                lambda aml: (
                    aml.product_id
                    and aml.display_type in (False, 'product')
                    and (aml.quantity or 0.0)
                )
            ):
                vals = bill._qfm_prepare_cost_history_values(line)
                if not vals:
                    continue
                existing = History.search([
                    ('account_move_line_id', '=', line.id),
                ], limit=1)
                if existing:
                    existing.write(vals)
                else:
                    History.create(vals)

    def _qfm_prepare_cost_history_values(self, line):
        self.ensure_one()
        product = line.product_id
        if not product:
            return {}

        company = self.company_id or self.env.company
        currency = line.currency_id or self.currency_id or company.currency_id
        bill_date = self.invoice_date or self.date or fields.Date.context_today(self)
        source_uom = (
            line.product_uom_id
            if 'product_uom_id' in line._fields and line.product_uom_id
            else product.uom_id
        )
        discount = line.discount if 'discount' in line._fields else 0.0
        invoice_unit_cost = (line.price_unit or 0.0) * (1.0 - (discount or 0.0) / 100.0)
        cost = convert_unit_price(
            invoice_unit_cost,
            source_uom,
            product.uom_id,
            currency,
            currency,
            company,
            bill_date,
        )

        receipt_move = self._qfm_get_invoice_line_receipt_move(line)
        purchase_line = (
            line.purchase_line_id
            if 'purchase_line_id' in line._fields and line.purchase_line_id
            else self.env['purchase.order.line']
        )
        purchase_order = purchase_line.order_id if purchase_line else self.env['purchase.order']
        receipt_date = (
            self._qfm_get_stock_move_datetime(receipt_move)
            or fields.Datetime.to_datetime(bill_date)
        )

        references = []
        for value in (
            self.name if self.name and self.name != '/' else False,
            self.ref,
            purchase_order.name if purchase_order else False,
        ):
            if value and value not in references:
                references.append(value)

        return {
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_id': product.id,
            'date': receipt_date,
            'cost': cost,
            'currency_id': currency.id,
            'reference': ' / '.join(references) or self.display_name,
            'account_move_id': self.id,
            'account_move_line_id': line.id,
            'purchase_order_id': purchase_order.id if purchase_order else False,
            'purchase_line_id': purchase_line.id if purchase_line else False,
            'picking_id': receipt_move.picking_id.id if receipt_move and receipt_move.picking_id else False,
            'stock_move_id': receipt_move.id if receipt_move else False,
            'company_id': company.id,
        }

    def _qfm_get_invoice_line_receipt_move(self, line):
        purchase_line = (
            line.purchase_line_id
            if 'purchase_line_id' in line._fields and line.purchase_line_id
            else self.env['purchase.order.line']
        )
        if not purchase_line or 'move_ids' not in purchase_line._fields:
            return self.env['stock.move']

        moves = purchase_line.move_ids.filtered(
            lambda move: move.state == 'done' and move.product_id == line.product_id
        )
        incoming_moves = moves.filtered(
            lambda move: (
                move.location_id.usage == 'supplier'
                or (move.picking_id and move.picking_id.picking_type_code == 'incoming')
            )
        )
        moves = incoming_moves or moves
        if not moves:
            return self.env['stock.move']

        sorted_moves = moves.sorted(
            key=lambda move: (
                self._qfm_get_stock_move_datetime(move)
                or fields.Datetime.to_datetime(move.write_date)
                or fields.Datetime.to_datetime(move.create_date)
                or datetime.min,
                move.id,
            ),
            reverse=True,
        )
        return sorted_moves[:1]

    @staticmethod
    def _qfm_get_stock_move_datetime(move):
        if not move:
            return False
        if 'date' in move._fields and move.date:
            return fields.Datetime.to_datetime(move.date)
        picking = move.picking_id if 'picking_id' in move._fields else False
        if picking and 'date_done' in picking._fields and picking.date_done:
            return fields.Datetime.to_datetime(picking.date_done)
        if move.write_date:
            return fields.Datetime.to_datetime(move.write_date)
        return False
