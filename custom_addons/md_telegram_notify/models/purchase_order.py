import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)

PARAM_PO_THRESHOLD = "md_telegram.purchase_threshold"


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        # super() primero: si la confirmacion falla (validacion, stock, reglas),
        # no debe salir ninguna alerta.
        res = super().button_confirm()
        self._md_telegram_notify_high_value()
        return res

    def _md_telegram_notify_high_value(self):
        """Encola una alerta por cada orden confirmada que supere el umbral.

        Encolar participa de la MISMA transaccion que la confirmacion, y eso es
        deliberado: si el pedido acaba haciendo rollback, la alerta desaparece
        con el. Lo que queda fuera de la transaccion es el POST HTTP, que hace
        el cron. Telegram caido => la compra se confirma igual.
        """
        threshold = float(
            self.env["ir.config_parameter"].sudo().get_param(PARAM_PO_THRESHOLD) or 0.0
        )
        if threshold <= 0:
            return

        Message = self.env["md.telegram.message"]
        for order in self.filtered(lambda o: o.state in ("purchase", "done")):
            company = order.company_id
            company_currency = company.currency_id
            amount = order.currency_id._convert(
                order.amount_total,
                company_currency,
                company,
                order.date_order.date() if order.date_order else fields.Date.context_today(order),
            )
            if amount < threshold:
                continue

            body = _(
                "🔴 <b>Orden de compra de alto valor confirmada</b>\n\n"
                "<b>Documento:</b> %(name)s\n"
                "<b>Proveedor:</b> %(partner)s\n"
                "<b>Importe:</b> %(amount)s\n"
                "<b>Confirmada por:</b> %(user)s\n"
                "<b>Compania:</b> %(company)s",
                name=Message.escape(order.name),
                partner=Message.escape(order.partner_id.display_name),
                amount=Message.escape(company_currency.format(amount)),
                user=Message.escape(self.env.user.name),
                company=Message.escape(company.name),
            )
            order.telegram_notify(body, channel_code="compras")
