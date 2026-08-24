from odoo import _, api, fields, models
from odoo.exceptions import UserError

PARAM_BOT_TOKEN = "md_telegram.bot_token"
PARAM_PO_THRESHOLD = "md_telegram.purchase_threshold"
PARAM_SALE_THRESHOLD = "md_telegram.sale_threshold"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # El token se guarda en ir.config_parameter: un unico secreto por base de
    # datos, y su ACL ya limita la lectura a base.group_system. No se guarda en
    # res.company porque no es un dato por compania y multiplicarlo multiplica
    # la superficie de exposicion.
    md_telegram_bot_token = fields.Char(
        string="Bot Token",
        config_parameter=PARAM_BOT_TOKEN,
        help="Token que devuelve @BotFather al crear el bot (formato 123456789:AAH...).",
    )
    # NOTA Odoo 19: fields.Monetary NO es permitido en res.config.settings.
    # Se usa fields.Float con digitos de moneda (16, 2).
    md_telegram_po_threshold = fields.Float(
        string="Umbral de alerta en compras",
        config_parameter=PARAM_PO_THRESHOLD,
        digits=(16, 2),
        help="Se notifica al confirmar una orden de compra cuyo total iguale o supere "
             "este importe. 0 desactiva la alerta.",
    )
    md_telegram_sale_threshold = fields.Float(
        string="Umbral de alerta en ventas",
        config_parameter=PARAM_SALE_THRESHOLD,
        digits=(16, 2),
        help="Se notifica al confirmar una orden de venta cuyo total iguale o supere "
             "este importe. 0 desactiva la alerta. "
             "Configura tambien que canales reciben alertas de ventas en 'Canales de Telegram'.",
    )
    # Moneda de la compania para mostrar el simbolo en la vista.
    company_currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", readonly=True
    )

    def action_md_telegram_open_channels(self):
        return self.env["ir.actions.act_window"]._for_xml_id(
            "md_telegram_notify.action_md_telegram_channel"
        )

    def action_md_telegram_discover_chats(self):
        # Guardar antes: si el usuario acaba de pegar el token y no ha pulsado
        # "Guardar", getUpdates iria con el token viejo (o vacio).
        self.execute()
        return self.env["md.telegram.channel"].action_discover_chats()

    def action_md_telegram_webhook_info(self):
        """Muestra el estado del webhook directamente desde Ajustes."""
        self.execute()
        return self.env["md.telegram.channel"].action_webhook_info()

    def action_md_telegram_test(self):
        self.execute()
        channel = self.env["md.telegram.channel"].resolve("default")
        if not channel:
            raise UserError(
                _("No hay ningun canal configurado. Crea uno en Ajustes > Telegram > Canales.")
            )
        return channel.action_test_message()
