import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)

PARAM_SALE_THRESHOLD = "md_telegram.sale_threshold"


class SaleOrder(models.Model):
    """Extiende sale.order para enviar alertas Telegram al confirmar ventas.

    Comportamiento:
      - Solo notifica si el importe total de la venta (en moneda de la compania)
        es igual o superior al umbral configurado en md_telegram.sale_threshold.
      - Si el umbral es 0, las alertas de ventas estan desactivadas.
      - Solo notifica en los canales que tienen notify_on_sale = True.
    """

    _inherit = "sale.order"

    def action_confirm(self):
        # super() primero: si la confirmacion falla, no sale ninguna alerta.
        res = super().action_confirm()
        self._md_telegram_notify_sale()
        return res

    def _md_telegram_notify_sale(self):
        """Encola una alerta por cada venta confirmada que supere el umbral."""
        threshold = float(
            self.env["ir.config_parameter"].sudo().get_param(PARAM_SALE_THRESHOLD) or 0.0
        )
        if threshold <= 0:
            return

        channels = self.env["md.telegram.channel"].resolve_by_flag("notify_on_sale")
        if not channels:
            return

        Message = self.env["md.telegram.message"]
        for order in self.filtered(lambda o: o.state in ("sale", "done")):
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

            # URL de acceso directo (solo si Odoo es accesible desde el exterior).
            base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
            order_url = "%s/odoo/sales/%d" % (base_url.rstrip("/"), order.id) if base_url else ""

            body = _(
                "🟢 <b>Venta confirmada</b>\n\n"
                "<b>Documento:</b> %(name)s\n"
                "<b>Cliente:</b> %(partner)s\n"
                "<b>Importe:</b> %(amount)s\n"
                "<b>Vendedor:</b> %(user)s\n"
                "<b>Compania:</b> %(company)s"
            ) % {
                "name":    Message.escape(order.name),
                "partner": Message.escape(order.partner_id.display_name),
                "amount":  Message.escape(company_currency.format(amount)),
                "user":    Message.escape(order.user_id.name or self.env.user.name),
                "company": Message.escape(company.name),
            }

            # Botones de accion rapida si hay URL disponible.
            reply_markup = None
            if order_url:
                reply_markup = {
                    "inline_keyboard": [[
                        {"text": "Ver en Odoo", "url": order_url},
                    ]]
                }

            for channel in channels:
                Message.enqueue(
                    body=body,
                    channel=channel,
                    reply_markup=reply_markup,
                )
            _logger.info(
                "Telegram: alerta de venta encolada para orden %s (%.2f %s).",
                order.name, amount, company_currency.name,
            )
