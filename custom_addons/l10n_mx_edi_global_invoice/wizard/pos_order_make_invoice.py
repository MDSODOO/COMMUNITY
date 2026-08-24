# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.fields import Command
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class PosOrderMakeInv(models.TransientModel):
    _name = "pos.order.make.inv"
    _description = "Modelo que crea las facturas globales"

    count = fields.Integer(string="Numero de órdenes", compute="_compute_count")
    pos_order_ids = fields.Many2many(
        "pos.order", default=lambda self: self.env.context.get("active_ids")
    )

    fecha_factura = fields.Date(
        "Fecha de factura", default=lambda self: fields.Date.context_today(self)
    )

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Diario",
        compute="_compute_journal_id",
        readonly=False,
        store=True,
        domain=[("type", "=", "sale")],
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Cliente",
        compute="_compute_partner_id",
        readonly=False,
        store=True,
    )

    amount = fields.Float(
        string="Monto Total de las ordenes seleccionadas",
        help="Suma total de las ordenes.",
        compute="_compute_amount_total",
        store=True,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency", compute="_compute_currency_id", store=True
    )

    company_id = fields.Many2one(
        comodel_name="res.company", compute="_compute_company_id", store=True
    )

    # === COMPUTE METHODS ===#

    @api.depends("pos_order_ids")
    def _compute_count(self):
        for wizard in self:
            wizard.count = len(wizard.pos_order_ids)

    @api.depends("pos_order_ids")
    def _compute_currency_id(self):
        for wizard in self:
            currencies = wizard.pos_order_ids.mapped("currency_id")
            wizard.currency_id = currencies[0] if len(currencies) == 1 else False

    @api.depends("pos_order_ids")
    def _compute_amount_total(self):
        for wizard in self:
            wizard.amount = sum(wizard.pos_order_ids.mapped("amount_total"))

    @api.depends("pos_order_ids")
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = (
                wizard.pos_order_ids[:1].company_id.id
                if wizard.pos_order_ids
                else False
            )

    @api.depends("company_id")
    def _compute_journal_id(self):
        self.journal_id = False
        for wizard in self:
            if wizard.company_id and wizard.company_id.journal_inv_global_id:
                wizard.journal_id = wizard.company_id.journal_inv_global_id.id

    @api.depends("company_id")
    def _compute_partner_id(self):
        self.partner_id = False
        for wizard in self:
            if wizard.company_id and wizard.company_id.partner_inv_global_id:
                wizard.partner_id = wizard.company_id.partner_inv_global_id.id

    # === ACTION METHODS ===#

    def create_invoices(self):
        self.ensure_one()
        if not self.pos_order_ids:
            raise ValidationError(_("No hay órdenes POS seleccionadas."))
        if not all(order._name == "pos.order" for order in self.pos_order_ids):
            raise ValidationError(
                _("Solo se pueden procesar órdenes POS. Seleccione registros válidos.")
            )
        companies = self.pos_order_ids.mapped("company_id")
        company_id = companies[0] if companies else False
        if len(companies) > 1:
            str_incorrectas = ""
            for order in self.pos_order_ids:
                str_incorrectas += f"\t{order.name} ({order.company_id.name})\n"

            raise ValidationError(
                _(
                    "¡Advertencia!\n"
                    "No se puede completar la operación porque las órdenes pertenecen a distintas empresas:\n%s",
                    str_incorrectas,
                )
            )

        orders_incorrectas = self.pos_order_ids.filtered(
            lambda x: x.state not in ["paid", "done"]
        )
        if len(orders_incorrectas) > 0:
            str_incorrectas = ""
            for order in orders_incorrectas:
                str_incorrectas += "\t" + str(order.name) + "\n"
            raise ValidationError(
                _(
                    "¡Advertencia!, No se puede completar la operacion por que las siguientes ordenes no estan en estado pagado o publicado\n %s",
                    str_incorrectas,
                )
            )

        orders_not_to_invoice = self.pos_order_ids.filtered(
            lambda x: x.invoice_status not in ["to_invoice"]
        )
        if len(orders_not_to_invoice) > 0:
            str_incorrectas = ""
            for order in orders_not_to_invoice:
                str_incorrectas += "\t" + str(order.name) + "\n"
            raise ValidationError(
                _(
                    "¡Advertencia!, No se puede completar la operacion por que las siguientes ordenes no estan en estado de factura por facturar\n %s",
                    str_incorrectas,
                )
            )

        orders_con_reembolso = self.pos_order_ids.filtered(
            lambda x: x.refund_orders_count > 0
        )
        _logger.info("ORDENES CON REEMBOLSO %s", orders_con_reembolso)
        for order_c_rembolso in orders_con_reembolso:
            if (
                len(
                    order_c_rembolso.lines.filtered(
                        lambda x: (x.qty - x.refunded_qty) > 0
                    )
                )
                == 0
            ):
                raise ValidationError(
                    _(
                        "¡Advertencia!, No se puede completar la operacion por que las siguientes ordenes han sido reembolsadas completamente\n %s",
                        order_c_rembolso.name,
                    )
                )

        orders_zero = self.pos_order_ids.filtered(lambda x: x.amount_total <= 0)
        if len(orders_zero) > 0:
            str_incorrectas = ""
            for order in orders_zero:
                str_incorrectas += "\t" + str(order.name) + "\n"
            raise ValidationError(
                _(
                    "¡Advertencia!, No se puede completar la operacion por que las siguientes ordenes son menores o igual a 0\n %s",
                    str_incorrectas,
                )
            )

        data_create = {
            "move_type": "out_invoice",
            "invoice_date": self.fecha_factura,
            "invoice_date_due": self.fecha_factura,
            "partner_id": self.partner_id.id,
            "journal_id": self.journal_id.id,
            "is_global_invoice": True,
            "company_id": company_id.id,
        }
        data_lines = []
        move_type = "out_invoice"
        ordenes_contempladas = self.pos_order_ids
        _logger.info("ORDENES_CONTEMPLADAS %s", ordenes_contempladas)
        for order in ordenes_contempladas:
            lines = order._prepare_invoice_lines(move_type)
            data_lines += lines

        data_create["invoice_line_ids"] = data_lines
        inv = self.env["account.move"].sudo().create(data_create)
        if inv.move_type != "out_invoice":
            raise ValidationError(
                _(
                    "Error crítico: Se intentó crear una factura de tipo '%s'. Solo se aceptan facturas de cliente (out_invoice)."
                )
                % inv.move_type
            )
        if inv:
            orders_without_partner = self.pos_order_ids.filtered(
                lambda o: not o.partner_id
            )
            if orders_without_partner:
                orders_without_partner.sudo().write(
                    {"partner_id": company_id.partner_inv_global_id.id}
                )
            self.pos_order_ids.sudo().write(
                {"account_move": inv.id, "invoice_status": "invoiced"}
            )
            self._post_and_reconcile_invoice(inv, ordenes_contempladas, company_id)

        action = {
            "name": _("Facturas Globales"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "target": "current",
            "res_id": inv.id,
            "view_mode": "form",
            "views": [(self.env.ref("account.view_move_form").id, "form")],
        }

        return action

    def _post_and_reconcile_invoice(self, invoice, orders, company):
        invoice.action_post()
        orders_by_session = {}
        for order in orders:
            orders_by_session.setdefault(order.session_id, []).append(order)

        payment_moves_from_closed_sessions = {}
        all_payment_moves = self.env["account.move"]
        for session, session_orders in orders_by_session.items():
            is_session_closed = session.state == "closed"
            for order in session_orders:
                order_payments = order.payment_ids.sudo().with_company(company)
                payment_moves = order_payments._create_payment_moves(is_session_closed)
                all_payment_moves |= payment_moves
                if is_session_closed:
                    payment_moves_from_closed_sessions[order] = payment_moves

        orders._reconcile_invoice_payments(invoice, all_payment_moves)

        for order, payment_moves in payment_moves_from_closed_sessions.items():
            order._create_misc_reversal_move(payment_moves)
