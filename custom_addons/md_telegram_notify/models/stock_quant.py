import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

PARAM_STOCK_ALERT_DAYS = "md_telegram.stock_alert_days_ahead"


class StockQuant(models.Model):
    """Extiende stock.quant para generar alertas de stock minimo por Telegram.

    El cron diario busca ubicaciones de tipo 'internal' donde la cantidad
    disponible (qty_available en product.product) es igual o inferior al
    punto de reorden definido en stock.warehouse.orderpoint.
    """

    _inherit = "stock.quant"

    @api.model
    def _cron_telegram_low_stock(self):
        """Cron diario: envia digest de productos bajo punto de reorden.

        Se ejecuta una vez al dia (ver ir_cron_stock.xml). Si no hay canales
        con notify_on_stock_alert activo, el metodo termina sin hacer nada.
        """
        channels = self.env["md.telegram.channel"].sudo().search(
            [("notify_on_stock_alert", "=", True), ("active", "=", True)]
        )
        if not channels:
            _logger.debug(
                "Telegram stock alert: no hay canales con notify_on_stock_alert activo, saltando."
            )
            return

        # Buscar puntos de reorden activos con stock por debajo del minimo.
        orderpoints = self.env["stock.warehouse.orderpoint"].sudo().search(
            [("active", "=", True)]
        )
        if not orderpoints:
            return

        low_stock_lines = []
        for op in orderpoints:
            product = op.product_id
            qty = product.with_context(
                location=op.location_id.id
            ).qty_available
            if qty <= op.product_min_qty:
                low_stock_lines.append({
                    "product": product.display_name,
                    "qty": qty,
                    "min_qty": op.product_min_qty,
                    "uom": op.product_uom.name,
                    "location": op.location_id.complete_name,
                })

        if not low_stock_lines:
            _logger.debug("Telegram stock alert: todos los productos estan sobre el minimo.")
            return

        # Construir mensaje digest agrupado.
        lines_html = "\n".join(
            "  • <b>%s</b> — %.2f %s (min: %.2f) en %s" % (
                self.env["md.telegram.message"].escape(item["product"]),
                item["qty"],
                self.env["md.telegram.message"].escape(item["uom"]),
                item["min_qty"],
                self.env["md.telegram.message"].escape(item["location"]),
            )
            for item in low_stock_lines
        )
        total = len(low_stock_lines)
        body = _(
            "⚠️ <b>Alerta de stock bajo</b>\n"
            "<b>%(total)s producto(s)</b> por debajo del punto de reorden:\n\n"
            "%(lines)s\n\n"
            "<i>Generado automaticamente por Odoo · %(date)s</i>"
        ) % {
            "total": total,
            "lines": lines_html,
            "date": fields.Date.context_today(self).strftime("%d/%m/%Y"),
        }

        for channel in channels:
            self.env["md.telegram.message"].enqueue(
                body=body,
                channel=channel,
            )
        _logger.info(
            "Telegram stock alert: digest de %s productos enviado a %s canal(es).",
            total, len(channels),
        )
