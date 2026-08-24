import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

PARAM_BOT_TOKEN = "md_telegram.bot_token"
PARAM_SALE_THRESHOLD = "md_telegram.sale_threshold"


class MdTelegramChannel(models.Model):
    """Destino de una alerta: un grupo, canal o chat privado de Telegram.

    El token del bot NO vive aqui (es uno solo para toda la instalacion y es
    secreto): va en ir.config_parameter, cuyo ACL en Odoo ya restringe la
    lectura a Ajustes/Administracion.

    --- Fase 2 (2026-08): notificaciones de ventas y stock, info de webhook ---
    Se anadieron:
      - notify_on_sale: activa alertas al confirmar ordenes de venta.
      - notify_on_stock_alert: recibe los digests de stock bajo minimo.
      - action_webhook_info(): muestra la URL del webhook registrado en Telegram.
      - send_photo(): shortcut para encolar una foto directamente.
      - send_document(): shortcut para encolar un documento directamente.
    """

    _name = "md.telegram.channel"
    _description = "Canal de Telegram"
    _order = "sequence, name"

    name = fields.Char(string="Nombre", required=True, translate=False)
    code = fields.Char(
        string="Codigo",
        required=True,
        help="Identificador tecnico usado desde el codigo, p. ej. 'compras'. "
        "Si un codigo no existe se usa el canal 'default'.",
    )
    chat_id = fields.Char(
        string="Chat ID",
        required=True,
        help="ID numerico del grupo, siempre negativo (-100...). Se obtiene con el "
        "boton 'Detectar chats' tras escribir /start@tu_bot dentro del grupo. "
        "Si el grupo se promociona a supergrupo el ID cambia, pero el modulo lo "
        "detecta al primer envio y lo actualiza solo.",
    )
    is_group = fields.Boolean(
        string="Es un grupo", compute="_compute_is_group", store=False,
        help="Los grupos tienen ID negativo; los chats privados, positivo.",
    )
    message_thread_id = fields.Char(
        string="Tema (thread ID)",
        help="Solo para grupos con Temas activados: ID del tema al que dirigir el "
        "mensaje. Vacio = el tema General.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Char(string="Descripcion")
    message_count = fields.Integer(string="Mensajes", compute="_compute_message_count")

    # --- Nuevo Fase 2: configuracion de alertas por canal ---
    notify_on_sale = fields.Boolean(
        string="Alertas de ventas",
        default=False,
        help="Si esta activo, este canal recibe una notificacion cada vez que "
             "se confirma una orden de venta que supera el umbral configurado.",
    )
    notify_on_stock_alert = fields.Boolean(
        string="Alertas de stock minimo",
        default=False,
        help="Si esta activo, este canal recibe el digest diario de productos "
             "por debajo de su punto de reorden.",
    )
    notify_on_lot_expiry = fields.Boolean(
        string="Alertas de caducidad de lotes",
        default=False,
        help="Si esta activo, este canal recibe el digest diario de lotes "
             "cuya fecha de caducidad es igual o inferior a 30 dias.",
    )

    # Odoo 19: _sql_constraints ya no se aplica; usar models.Constraint.
    _code_uniq = models.Constraint(
        "UNIQUE(code)",
        "Ya existe un canal de Telegram con ese codigo.",
    )

    @api.depends("chat_id")
    def _compute_is_group(self):
        for channel in self:
            channel.is_group = (channel.chat_id or "").strip().startswith("-")

    def _compute_message_count(self):
        data = self.env["md.telegram.message"].sudo()._read_group(
            [("channel_id", "in", self.ids)], groupby=["channel_id"], aggregates=["__count"]
        )
        counts = {channel.id: count for channel, count in data}
        for channel in self:
            channel.message_count = counts.get(channel.id, 0)

    @api.constrains("chat_id")
    def _check_chat_id(self):
        for channel in self:
            value = (channel.chat_id or "").strip()
            if not (value.lstrip("-").isdigit() or value.startswith("@")):
                raise ValidationError(
                    _("El Chat ID debe ser un numero (p. ej. -1001234567890) o '@canal_publico'.")
                )

    # ------------------------------------------------------------------
    # Resolucion y credenciales
    # ------------------------------------------------------------------
    @api.model
    def resolve(self, code):
        """Devuelve el canal para `code`, con respaldo en el canal 'default'."""
        if not code:
            code = "default"
        channel = self.sudo().search([("code", "=", code)], limit=1)
        if not channel and code != "default":
            channel = self.sudo().search([("code", "=", "default")], limit=1)
        return channel

    @api.model
    def resolve_by_flag(self, flag_field):
        """Devuelve todos los canales activos que tienen el campo booleano activo.

        Uso: self.env['md.telegram.channel'].resolve_by_flag('notify_on_sale')
        """
        return self.sudo().search([(flag_field, "=", True)])

    @api.model
    def _get_bot_token(self):
        return (self.env["ir.config_parameter"].sudo().get_param(PARAM_BOT_TOKEN) or "").strip()

    # ------------------------------------------------------------------
    # Shortcuts de envio multimedia
    # ------------------------------------------------------------------
    def send_photo(self, url_or_file_id, caption="", parse_mode="HTML",
                   reply_markup=None, channel_code=None):
        """Encola una foto en este canal (o en el canal con el codigo dado).

        :param url_or_file_id: URL publica de la imagen o file_id de Telegram.
        :param caption: texto HTML que acompana la imagen (max 1024 chars).
        :param reply_markup: dict con InlineKeyboardMarkup u otro markup.
        :param channel_code: si se provee, resuelve el canal por codigo en vez
            de usar self.

        Uso rapido desde cualquier modelo:
            self.env['md.telegram.channel'].send_photo(
                'https://mi.dominio/imagen.jpg',
                caption='<b>Reporte del dia</b>',
                reply_markup={'inline_keyboard': [[
                    {'text': 'Ver en Odoo', 'url': 'https://...'}
                ]]},
                channel_code='ventas',
            )
        """
        channel = self if self and not channel_code else self.env["md.telegram.channel"].resolve(channel_code)
        return self.env["md.telegram.message"].enqueue(
            body=caption,
            channel=channel,
            parse_mode=parse_mode,
            message_type="photo",
            media_url=url_or_file_id,
            reply_markup=reply_markup,
        )

    def send_document(self, url_or_file_id, caption="", parse_mode="HTML",
                      reply_markup=None, channel_code=None):
        """Encola un documento (PDF, Excel, etc.) en este canal.

        :param url_or_file_id: URL publica del documento o file_id de Telegram.
        :param caption: texto HTML que acompana el documento (max 1024 chars).
        """
        channel = self if self and not channel_code else self.env["md.telegram.channel"].resolve(channel_code)
        return self.env["md.telegram.message"].enqueue(
            body=caption,
            channel=channel,
            parse_mode=parse_mode,
            message_type="document",
            media_url=url_or_file_id,
            reply_markup=reply_markup,
        )

    # ------------------------------------------------------------------
    # Acciones de UI
    # ------------------------------------------------------------------
    def action_test_message(self):
        """Envio sincrono de prueba: aqui si queremos el error en pantalla."""
        self.ensure_one()
        message = self.env["md.telegram.message"].enqueue(
            body=_("<b>Prueba de alertas Odoo</b>\nCanal: %s\nSi lees esto, la configuracion es correcta.")
            % self.env["md.telegram.message"].escape(self.name),
            channel=self,
        )
        if not message:
            raise UserError(_("No se pudo encolar el mensaje: revisa que el canal este activo."))
        message.action_send_now()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": _("Mensaje de prueba enviado a %s.", self.name),
                "sticky": False,
            },
        }

    def action_test_photo(self):
        """Envio sincrono de prueba con una foto de placeholder."""
        self.ensure_one()
        # Foto de prueba publica de Telegram (logo oficial)
        test_url = "https://telegram.org/img/t_logo.png"
        reply_markup = {
            "inline_keyboard": [[
                {"text": "Ver Odoo", "url": "https://odoo.bodegademedicamentos.com/web"},
                {"text": "Documentacion", "url": "https://core.telegram.org/bots/api"},
            ]]
        }
        message = self.env["md.telegram.message"].enqueue(
            body=_(
                "<b>Prueba multimedia</b>\n"
                "Canal: %s\n"
                "Si ves esta imagen y los botones, la integracion multimedia funciona."
            ) % self.env["md.telegram.message"].escape(self.name),
            channel=self,
            message_type="photo",
            media_url=test_url,
            reply_markup=reply_markup,
        )
        if not message:
            raise UserError(_("No se pudo encolar el mensaje de prueba multimedia."))
        message.action_send_now()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": _("Foto de prueba enviada a %s.", self.name),
                "sticky": False,
            },
        }

    @api.model
    def action_webhook_info(self):
        """Consulta el estado del webhook registrado en Telegram y lo muestra.

        Util para diagnosticar si hay un webhook activo que podria competir
        con getUpdates (solo puede usarse uno de los dos a la vez).
        """
        token = self._get_bot_token()
        if not token:
            raise UserError(_("Configura primero el Bot Token en Ajustes > Telegram."))
        try:
            response = requests.get(
                "https://api.telegram.org/bot%s/getWebhookInfo" % token, timeout=(5, 15)
            )
            data = response.json()
        except (requests.exceptions.RequestException, ValueError) as exc:
            raise UserError(_("No se pudo contactar con Telegram: %s", exc)) from exc

        if not data.get("ok"):
            raise UserError(_("Telegram rechazo la peticion: %s", data.get("description")))

        info = data.get("result", {})
        url = info.get("url") or _("(ninguno registrado)")
        pending = info.get("pending_update_count", 0)
        last_error = info.get("last_error_message") or _("sin errores")
        last_error_date = info.get("last_error_date") or ""
        allowed_updates = ", ".join(info.get("allowed_updates") or ["todos"])

        raise UserError(
            _(
                "Estado del Webhook de Telegram:\n\n"
                "URL registrada: %(url)s\n"
                "Actualizaciones pendientes: %(pending)s\n"
                "Ultimo error: %(error)s (%(date)s)\n"
                "Tipos permitidos: %(allowed)s\n\n"
                "Nota: si hay URL registrada, getUpdates no funciona. "
                "Para usar el polling del modulo, elimina el webhook con:\n"
                "curl https://api.telegram.org/bot<TOKEN>/deleteWebhook"
            )
            % {
                "url": url,
                "pending": pending,
                "error": last_error,
                "date": last_error_date,
                "allowed": allowed_updates,
            }
        )

    @api.model
    def action_discover_chats(self):
        """Lee getUpdates y muestra los chats donde el bot ha sido activado."""
        token = self._get_bot_token()
        if not token:
            raise UserError(_("Configura primero el Bot Token en Ajustes > Telegram."))
        try:
            response = requests.get(
                "https://api.telegram.org/bot%s/getUpdates" % token, timeout=(5, 15)
            )
            data = response.json()
        except (requests.exceptions.RequestException, ValueError) as exc:
            raise UserError(_("No se pudo contactar con Telegram: %s", exc)) from exc

        if not data.get("ok"):
            raise UserError(_("Telegram rechazo la peticion: %s", data.get("description")))

        chats = {}
        for update in data.get("result", []):
            for key in ("message", "channel_post", "my_chat_member"):
                chat = (update.get(key) or {}).get("chat")
                if chat:
                    chats[chat["id"]] = (
                        chat.get("title") or chat.get("username") or _("Chat privado"),
                        chat.get("type") or "",
                    )

        if not chats:
            raise UserError(
                _(
                    "Telegram no devolvio ningun chat.\n\n"
                    "Anade el bot al grupo y escribe alli '/start@tu_bot' (con la @). "
                    "Por el privacy mode el bot no ve los mensajes normales, solo "
                    "los comandos y las menciones."
                )
            )

        def _sort_key(item):
            return (0 if item[1][1] in ("group", "supergroup") else 1, item[1][0])

        lines = []
        for chat_id, (title, chat_type) in sorted(chats.items(), key=_sort_key):
            mark = "GRUPO  " if chat_type in ("group", "supergroup") else "       "
            lines.append("%s%s  ->  %s (%s)" % (mark, chat_id, title, chat_type or "?"))

        raise UserError(
            _(
                "Chats detectados. Copia el ID del GRUPO (empieza con guion):\n\n%s\n\n"
                "Si el grupo aparece como 'group' y no 'supergroup', ten en cuenta "
                "que su ID cambiara si Telegram lo promociona a supergrupo. El "
                "modulo lo detecta y se reconfigura solo."
            )
            % "\n".join(lines)
        )

    def action_view_messages(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Mensajes de %s", self.name),
            "res_model": "md.telegram.message",
            "view_mode": "list,form",
            "domain": [("channel_id", "=", self.id)],
        }
