import logging
import decimal
from collections import defaultdict

from odoo import _, api, Command, fields, models
from lxml import etree
import logging
import datetime

_logger = logging.getLogger(__name__)


class PosSessionInherit(models.Model):
    _inherit = "pos.session"

    make_global_invs = fields.Boolean(
        "Realizar factura global al cierre?", default=False
    )
    global_inv_generated = fields.Boolean("Factura global generada", default=False)

    @api.model
    def set_option_global_inv_active(self, session_id, do_global_inv):
        session = self.browse(session_id)
        if session:
            session.make_global_invs = do_global_inv
            return 1
        return 0

    def get_orders_uninvoiced(self):
        if self and self.config_id and self.config_id.active_facturacion_global:
            orders = self.env["pos.order"].search(
                [("session_id", "=", self.id), ("state", "in", ["paid", "posted"])]
            )
            orders = orders.filtered(
                lambda order: order.invoice_status in ("to_invoice")
            )
            return len(orders)
        return 0

    def make_invoice_global_with_uninvoiced_orders(self):
        orders_global = self.env["pos.order"].search(
            [("session_id", "=", self.id), ("state", "in", ["paid", "posted", "done"])]
        )
        orders_global = orders_global.filtered(
            lambda order: order.invoice_status in ("to_invoice")
        )
        if not orders_global:
            return False
        wizard = (
            self.env["pos.order.make.inv"]
            .sudo()
            .create(
                {
                    "pos_order_ids": [(6, 0, orders_global.ids)],
                    "fecha_factura": self.stop_at.date(),
                }
            )
        )
        wizard.create_invoices()
        inv = orders_global[0].account_move.filtered(lambda m: m.is_global_invoice)[:1]
        return inv.name if inv else True

    @api.model
    def _cron_generate_global_invoices(self):
        sessions = self.search(
            [
                ("state", "=", "closed"),
                ("make_global_invs", "=", True),
                ("global_inv_generated", "=", False),
            ]
        )
        for session in sessions:
            try:
                inv_name = session.make_invoice_global_with_uninvoiced_orders()
                session.global_inv_generated = True
                if inv_name:
                    session._notify_global_invoice(success=True, inv_name=inv_name)
            except Exception as e:
                _logger.error(
                    "Error generando factura global para sesión %s: %s",
                    session.name,
                    str(e),
                )
                session._notify_global_invoice(success=False, error_msg=str(e))

    def _notify_global_invoice(self, success, inv_name=None, error_msg=None):
        if success:
            summary = "Factura Global generada correctamente"
            note = (
                f"Sesión: {self.name}<br/>"
                f"Punto de venta: {self.config_id.name}<br/>"
                f"Factura: {inv_name}<br/>"
                f"Por favor revise y timbre la factura global generada."
            )
            subject = f"[Odoo] Factura Global generada — {self.name}"
            body = f"""
                <p>La factura global fue generada correctamente.</p>
                <ul>
                    <li><b>Sesión:</b> {self.name}</li>
                    <li><b>Punto de venta:</b> {self.config_id.name}</li>
                    <li><b>Factura:</b> {inv_name}</li>
                    <li><b>Fecha:</b> {self.stop_at.date()}</li>
                </ul>
                <p>Por favor revise y timbre la factura desde
                Facturación → Facturas de cliente.</p>
            """
        else:
            summary = "Error al generar Factura Global"
            note = f"Sesión: {self.name}<br/>Error: {error_msg}"
            subject = f"[Odoo] Error Factura Global — {self.name}"
            body = f"""
                <p>El cron de generación de factura global encontró un error.</p>
                <ul>
                    <li><b>Sesión:</b> {self.name}</li>
                    <li><b>Punto de venta:</b> {self.config_id.name}</li>
                    <li><b>Error:</b> {error_msg}</li>
                </ul>
                <p>Por favor revise y genere la factura global manualmente desde
                el listado de órdenes POS.</p>
            """
        session_user = self.user_id or self.env.user
        self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("pos.session"),
                "res_id": self.id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "summary": summary,
                "note": note,
                "user_id": session_user.id,
            }
        )
        self.env["mail.mail"].sudo().create(
            {
                "subject": subject,
                "body_html": body,
                "email_to": session_user.partner_id.email,
            }
        ).send()

    def close_session_from_ui(self, bank_payment_method_diff_pairs=None):
        """Calling this method will try to close the session.

        param bank_payment_method_diff_pairs: list[(int, float)]
            Pairs of payment_method_id and diff_amount which will be used to post
            loss/profit when closing the session.

        If successful, it returns {'successful': True}
        Otherwise, it returns {'successful': False, 'message': str, 'redirect': bool}.
        'redirect' is a boolean used to know whether we redirect the user to the back end or not.
        When necessary, error (i.e. UserError, AccessError) is raised which should redirect the user to the back end.
        """
        return super().close_session_from_ui(
            bank_payment_method_diff_pairs=bank_payment_method_diff_pairs
        )
