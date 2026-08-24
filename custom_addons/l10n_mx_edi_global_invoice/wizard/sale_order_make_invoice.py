# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.fields import Command
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class SaleOrderMakeInv(models.TransientModel):
    _name = "sale.order.make.inv"
    _description = "Modelo que crea las facturas globales"

    count = fields.Integer(string="Numero de órdenes", compute="_compute_count")
    sale_order_ids = fields.Many2many(
        "sale.order", default=lambda self: self.env.context.get("active_ids")
    )

    fecha_factura = fields.Date(
        "Fecha de factura", default=lambda self: fields.Date.context_today(self)
    )

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Diario",
        compute="_compute_journal_id",
        domain="[('type', '=', 'sale')]",
        readonly=False,
        store=True,
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

    @api.depends("sale_order_ids")
    def _compute_count(self):
        for wizard in self:
            wizard.count = len(wizard.sale_order_ids)

    @api.depends("sale_order_ids")
    def _compute_currency_id(self):
        for wizard in self:
            currencys = set()
            for pos_order in wizard.sale_order_ids:
                currencys.add(pos_order.currency_id.id)
            if len(currencys) == 1:
                wizard.currency_id = list(currencys)[0]

    @api.depends("sale_order_ids")
    def _compute_amount_total(self):
        for wizard in self:
            wizard.amount = sum([pos.amount_total for pos in wizard.sale_order_ids])

    @api.depends("sale_order_ids")
    def _compute_company_id(self):
        self.company_id = False
        for wizard in self:
            if wizard.sale_order_ids:
                wizard.company_id = wizard.sale_order_ids[0].company_id.id
                continue

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
        if not self.sale_order_ids:
            raise ValidationError(_("No hay órdenes de venta seleccionadas."))
        if not all(order._name == "sale.order" for order in self.sale_order_ids):
            raise ValidationError(
                _(
                    "Solo se pueden procesar órdenes de venta. Seleccione registros válidos."
                )
            )
        orders_incorrectas = self.sale_order_ids.filtered(
            lambda x: x.state not in ["sale", "done"] or x.invoice_status == "invoiced"
        )
        if len(orders_incorrectas) > 0:
            str_incorrectas = ""
            for order in orders_incorrectas:
                str_incorrectas += "\t" + str(order.name) + "\n"
            raise ValidationError(
                _(
                    "¡Advertencia!, No se puede completar la operacion por que las siguientes ordenes no estan en estado Orden de venta o Bloqueado, o ya estan facturadas por completo\n %s",
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
        }
        data_lines = []
        invoice_item_sequence = 0
        invoice_line_vals = []
        for order in self.sale_order_ids:
            invoiceable_lines = order._get_invoiceable_lines()

            if not any(not line.display_type for line in invoiceable_lines):
                continue

            down_payment_section_added = False
            for line in invoiceable_lines:
                if not down_payment_section_added and line.is_downpayment:
                    # Create a dedicated section for the down payments
                    # (put at the end of the invoiceable_lines)
                    invoice_line_vals.append(
                        Command.create(
                            order._prepare_down_payment_section_line(
                                sequence=invoice_item_sequence
                            )
                        ),
                    )
                    down_payment_section_added = True
                    invoice_item_sequence += 1
                invoice_line_vals.append(
                    Command.create(
                        line._prepare_invoice_line(sequence=invoice_item_sequence)
                    ),
                )
                invoice_item_sequence += 1

        data_create["invoice_line_ids"] = invoice_line_vals
        inv = self.env["account.move"].sudo().create(data_create)
        if inv.move_type != "out_invoice":
            raise ValidationError(
                _(
                    "Error crítico: Se intentó crear una factura de tipo '%s'. Solo se aceptan facturas de cliente (out_invoice)."
                )
                % inv.move_type
            )

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

    summary_html = fields.Html(
        string="Resumen", compute="_compute_summary_html", sanitize=False
    )

    @api.depends("sale_order_ids")
    def _compute_summary_html(self):
        for wizard in self:
            # Campo HTML por defecto si no hay órdenes
            if not wizard.sale_order_ids:
                wizard.summary_html = "<p>No hay órdenes seleccionadas.</p>"
                continue

            # Agrupar órdenes por partner
            partners = {}
            for so in wizard.sale_order_ids:
                partners.setdefault(so.partner_id, []).append(so)

            html = ['<div style="font-family:Arial, sans-serif; font-size:13px;">']
            html.append("<h3>Resumen de líneas por cliente</h3>")

            total_general = 0.0

            for partner, orders in partners.items():
                subtotal_partner = 0.0

                html.append(f"""
                    <div style="border:1px solid #ccc; padding:10px; margin-bottom:15px;">
                        <h4>Cliente: {partner.name}</h4>
                        <table style="width:100%; border-collapse: collapse;">
                            <thead>
                                <tr>
                                    <th style="border-bottom:1px solid #999; text-align:left; padding:6px;">Orden</th>
                                    <th style="border-bottom:1px solid #999; text-align:left; padding:6px;">Producto</th>
                                    <th style="border-bottom:1px solid #999; text-align:right; padding:6px;">Cantidad</th>
                                    <th style="border-bottom:1px solid #999; text-align:right; padding:6px;">Precio</th>
                                    <th style="border-bottom:1px solid #999; text-align:right; padding:6px;">Total c/Impuestos</th>
                                </tr>
                            </thead>
                            <tbody>
                """)

                for order in orders:
                    invoiceable_lines = order._get_invoiceable_lines()

                    # Lógica que usas para downpayments: saltar la "sección" que crea el primer downpayment
                    down_payment_section_added = False
                    for line in invoiceable_lines:
                        # Si aparece la sección de downpayment (se añade primero como sección),
                        # respetamos la lógica original: marcar que ya pasó y continuar.
                        if not down_payment_section_added and line.is_downpayment:
                            # NO mostramos la línea de sección en la tabla; marcamos y continuamos
                            down_payment_section_added = True
                            # Nota: la línea real de downpayment (is_downpayment=True) vendrá en otra iteración
                            # y será procesada normalmente aquí si corresponde.
                            continue

                        # Omitir líneas tipo sección/note (display_type truthy)
                        if line.display_type:
                            continue

                        # Cantidad y precio tal como se usarán en la factura
                        qty = getattr(
                            line, "qty_to_invoice", line.product_uom_qty or 0.0
                        )
                        price = getattr(line, "price_unit", 0.0)
                        discount = getattr(line, "discount", 0.0)

                        # ==== Preparar base_line para cálculo de impuestos (idéntico al nativo) ====
                        # Pasamos quantity=qty para que la función use la cantidad a facturar
                        base_line = line._prepare_base_line_for_taxes_computation(
                            quantity=qty,
                            # Aseguramos que use las taxes del propio line y la moneda/partner correctos:
                            tax_ids=line.tax_ids,
                            partner_id=order.partner_id,
                            currency_id=order.currency_id
                            or order.company_id.currency_id,
                            rate=getattr(order, "currency_rate", False),
                        )

                        # Añadir el detalle de impuestos al base_line (población de tax_details)
                        self.env["account.tax"]._add_tax_details_in_base_line(
                            base_line, line.company_id
                        )

                        # Obtener subtotal y total con impuestos desde tax_details (moneda de la orden)
                        price_subtotal = base_line.get("tax_details", {}).get(
                            "raw_total_excluded_currency", 0.0
                        )
                        price_total = base_line.get("tax_details", {}).get(
                            "raw_total_included_currency", 0.0
                        )
                        price_tax = price_total - price_subtotal

                        # Aumentar subtotales correspondientes
                        subtotal_partner += price_total

                        # Formateo: cantidad en forma compacta, precios con 2 decimales y separador de miles
                        qty_display = f"{qty:g}"
                        price_display = f"${price:,.2f}"
                        total_display = f"${price_total:,.2f}"

                        html.append(f"""
                            <tr>
                                <td style="padding:6px; border-top:1px solid #eee;">{order.name}</td>
                                <td style="padding:6px; border-top:1px solid #eee;">{line.product_id.display_name}</td>
                                <td style="padding:6px; border-top:1px solid #eee; text-align:right;">{qty_display}</td>
                                <td style="padding:6px; border-top:1px solid #eee; text-align:right;">{price_display}</td>
                                <td style="padding:6px; border-top:1px solid #eee; text-align:right;">{total_display}</td>
                            </tr>
                        """)

                total_general += subtotal_partner

                # Total por cliente (con impuestos)
                html.append(f"""
                            </tbody>
                        </table>
                        <p style="text-align:right; font-weight:bold; margin-top:10px;">
                            Total del cliente (c/IVA): ${subtotal_partner:,.2f}
                        </p>
                    </div>
                """)

            # Total general (con impuestos)
            html.append(f"""
                <hr/>
                <h3 style="text-align:right;">
                    TOTAL GENERAL (c/IVA): ${total_general:,.2f}
                </h3>
            """)
            html.append("</div>")

            wizard.summary_html = "".join(html)
