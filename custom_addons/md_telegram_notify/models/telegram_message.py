import json
import logging
from collections import defaultdict
from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)

API_URL = "https://api.telegram.org/bot%(token)s/%(method)s"
REQUEST_TIMEOUT = (5, 15)       # (connect, read) en segundos
MAX_ATTEMPTS = 5
BACKOFF_SECONDS = [60, 300, 900, 3600]  # espera antes del intento 2, 3, 4, 5
BATCH_SIZE = 50
STUCK_MINUTES = 15              # 'sending' huerfano -> vuelve a 'pending'
TELEGRAM_MAX_LEN = 4096

# Telegram limita a ~20 mensajes por minuto en un MISMO grupo (el limite global
# de 30/s no aplica aqui). Con el cron cada minuto, este tope evita provocar
# nosotros mismos los 429 en vez de reaccionar a ellos.
MAX_PER_CHAT_PER_RUN = 15

# Errores de Telegram que no tiene sentido reintentar: la causa es de
# configuracion, no transitoria. Reintentarlos solo llena el log.
PERMANENT_ERROR_CODES = (400, 401, 403, 404)

# Descripciones de 403 que significan "el bot ya no esta en el grupo".
KICKED_MARKERS = ("kicked", "blocked", "deactivated", "not a member", "chat not found")

# Mapa: message_type -> metodo de la Bot API de Telegram
API_METHOD_MAP = {
    "text":     "sendMessage",
    "photo":    "sendPhoto",
    "document": "sendDocument",
    "audio":    "sendAudio",
    "video":    "sendVideo",
}


class MdTelegramMessage(models.Model):
    """Cola de mensajes salientes hacia Telegram.

    El envio NUNCA ocurre dentro de la transaccion de negocio: quien notifica
    solo hace un INSERT en esta tabla (`enqueue`), y un cron aparte hace el
    POST HTTP en su propia transaccion. Asi una caida de api.telegram.org no
    puede bloquear ni revertir una confirmacion de pedido.

    --- Fase 2 (2026-08): soporte multimedia y botones ---
    Se anadieron:
      - message_type: text (por defecto), photo, document, audio, video.
      - media_url: URL del archivo cuando message_type != 'text'. Puede ser
        una URL publica o un file_id de Telegram (si ya esta subido).
      - reply_markup: JSON serializado de InlineKeyboardMarkup, ReplyKeyboard,
        ForceReply o ReplyKeyboardRemove. Se pasa directo a la API.
      - disable_notification: envio silencioso (sin sonido en el dispositivo).
      - protect_content: impide reenvio/guardado del mensaje.
    """

    _name = "md.telegram.message"
    _description = "Mensaje saliente de Telegram"
    _order = "id desc"

    channel_id = fields.Many2one(
        "md.telegram.channel", string="Canal", required=True, ondelete="restrict"
    )
    # Copia congelada: si manana cambian el chat_id del canal, el historico
    # sigue diciendo a donde se envio realmente este mensaje.
    chat_id = fields.Char(string="Chat ID", required=True, readonly=True)
    message_thread_id = fields.Char(string="Tema (thread)", readonly=True)
    body = fields.Text(string="Mensaje / Caption", required=True, readonly=True)
    parse_mode = fields.Selection(
        [("HTML", "HTML"), ("MarkdownV2", "MarkdownV2"), ("none", "Texto plano")],
        default="HTML",
        required=True,
        readonly=True,
    )

    # --- Nuevo Fase 2: tipo de mensaje y multimedia ---
    message_type = fields.Selection(
        [
            ("text",     "Texto"),
            ("photo",    "Foto"),
            ("document", "Documento"),
            ("audio",    "Audio"),
            ("video",    "Video"),
        ],
        default="text",
        required=True,
        readonly=True,
        string="Tipo de mensaje",
        help="Determina el metodo de la Bot API que se usa para el envio.",
    )
    media_url = fields.Char(
        string="URL / File ID del archivo",
        readonly=True,
        help="Para foto, documento, audio o video: URL publica o file_id de Telegram. "
             "Vacio para mensajes de texto.",
    )
    reply_markup = fields.Text(
        string="Reply Markup (JSON)",
        readonly=True,
        help="InlineKeyboardMarkup, ReplyKeyboardMarkup, etc. serializado como JSON. "
             "Ejemplo botones: "
             '{\"inline_keyboard\":[[{\"text\":\"Ver en Odoo\",\"url\":\"https://...\"}]]}',
    )
    disable_notification = fields.Boolean(
        string="Silencioso",
        default=False,
        readonly=True,
        help="Si esta activo el mensaje llega sin sonido ni vibracion.",
    )
    protect_content = fields.Boolean(
        string="Proteger contenido",
        default=False,
        readonly=True,
        help="Impide que los destinatarios reenvien o descarguen el contenido.",
    )

    # --- Campos de estado (sin cambios) ---
    state = fields.Selection(
        [
            ("pending",   "Pendiente"),
            ("sending",   "Enviando"),
            ("sent",      "Enviado"),
            ("failed",    "Fallido"),
            ("cancelled", "Cancelado"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    attempts = fields.Integer(string="Intentos", default=0, readonly=True)
    next_attempt = fields.Datetime(
        string="Proximo intento", default=fields.Datetime.now, index=True, readonly=True
    )
    sent_date = fields.Datetime(string="Enviado el", readonly=True)
    error_message = fields.Text(string="Ultimo error", readonly=True)
    telegram_message_id = fields.Char(string="ID en Telegram", readonly=True)

    # Trazabilidad: de que registro de Odoo salio esta alerta.
    res_model = fields.Char(string="Modelo origen", readonly=True)
    res_id = fields.Integer(string="ID origen", readonly=True)

    # ------------------------------------------------------------------
    # Utilidades estaticas
    # ------------------------------------------------------------------
    @staticmethod
    def escape(text):
        """Escapa texto para HTML de Telegram (parse_mode=HTML).

        Telegram solo requiere escapar <, > y &. No es el html_escape completo
        de Odoo, que tambien escapa ' y ".
        """
        return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------
    @api.model
    def enqueue(
        self,
        body,
        channel_code=None,
        channel=None,
        record=None,
        parse_mode="HTML",
        thread_id=None,
        message_type="text",
        media_url=None,
        reply_markup=None,
        disable_notification=False,
        protect_content=False,
    ):
        """Encola un mensaje. Operacion barata: un INSERT, cero red.

        :param body: texto del mensaje (ya formateado y escapado). Para
            mensajes multimedia actua como caption (max 1024 chars en Telegram).
        :param channel_code: codigo del canal destino (ver md.telegram.channel).
        :param channel: recordset de canal, alternativa a channel_code.
        :param record: registro de Odoo que origina la alerta (trazabilidad).
        :param message_type: 'text' | 'photo' | 'document' | 'audio' | 'video'.
        :param media_url: URL o file_id del archivo cuando type != 'text'.
        :param reply_markup: dict o JSON str con InlineKeyboardMarkup etc.
        :param disable_notification: bool, envia sin sonido.
        :param protect_content: bool, impide reenvio/descarga.
        :return: recordset de md.telegram.message (vacio si no hay canal activo).
        """
        Channel = self.env["md.telegram.channel"].sudo()
        channels = channel.sudo() if channel else Channel.resolve(channel_code)
        if not channels:
            _logger.warning(
                "Telegram: mensaje descartado, no hay canal activo para el codigo %r. "
                "Configuralo en Ajustes > Telegram.",
                channel_code,
            )
            return self.browse()

        body = (body or "").strip()
        if not body:
            return self.browse()

        # Limite de caption en multimedia es 1024; en texto es 4096.
        max_len = 1024 if message_type != "text" else TELEGRAM_MAX_LEN
        if len(body) > max_len:
            body = body[:max_len - 20] + "\n[...truncado]"

        # Serializar reply_markup a JSON si llega como dict.
        markup_str = None
        if reply_markup:
            if isinstance(reply_markup, dict):
                markup_str = json.dumps(reply_markup, ensure_ascii=False)
            else:
                markup_str = reply_markup  # ya es str

        vals_common = {
            "body": body,
            "parse_mode": parse_mode,
            "message_type": message_type,
            "media_url": media_url,
            "reply_markup": markup_str,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "res_model": record._name if record else False,
            "res_id": record.id if record else False,
        }

        messages = self.browse()
        for ch in channels:
            vals = dict(vals_common)
            vals["channel_id"] = ch.id
            vals["chat_id"] = ch.chat_id
            vals["message_thread_id"] = thread_id or ch.message_thread_id or False
            messages |= self.sudo().create(vals)
        return messages

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_dispatch(self):
        """Punto de entrada del cron de envio. Sin argumentos = compatible XML."""
        self._recover_stuck()
        messages = self._claim_batch()
        for message in messages:
            try:
                message._send_now()
            except Exception:
                _logger.exception(
                    "Telegram: excepcion no controlada al enviar id=%s", message.id
                )
                message.sudo().write({"state": "failed", "error_message": "Excepcion interna"})

    @api.model
    def _cron_gc(self):
        """Elimina mensajes muy antiguos (>90 dias) para no inflar la tabla."""
        cutoff = fields.Datetime.now() - timedelta(days=90)
        old = self.sudo().search(
            [("state", "in", ("sent", "cancelled", "failed")), ("create_date", "<", cutoff)]
        )
        count = len(old)
        old.unlink()
        if count:
            _logger.info("Telegram GC: %s mensajes purgados.", count)

    def _recover_stuck(self):
        """Devuelve a 'pending' los mensajes varados en 'sending' (worker muerto)."""
        cutoff = fields.Datetime.now() - timedelta(minutes=STUCK_MINUTES)
        stuck = self.sudo().search(
            [("state", "=", "sending"), ("write_date", "<", cutoff)]
        )
        if stuck:
            _logger.warning("Telegram: %s mensajes varados en 'sending', reponiendo.", len(stuck))
            stuck.write({"state": "pending"})

    def _select_batch_ids(self):
        """Selecciona los IDs del proximo lote con FOR UPDATE SKIP LOCKED."""
        self.env.cr.execute(
            """
            SELECT id, chat_id
              FROM md_telegram_message
             WHERE state = 'pending'
               AND next_attempt <= now() AT TIME ZONE 'UTC'
             ORDER BY id
             LIMIT %s
               FOR UPDATE SKIP LOCKED
            """,
            (BATCH_SIZE,),
        )
        per_chat = defaultdict(int)
        ids = []
        for message_id, chat_id in self.env.cr.fetchall():
            if per_chat[chat_id] >= MAX_PER_CHAT_PER_RUN:
                continue
            per_chat[chat_id] += 1
            ids.append(message_id)
        return ids

    @api.model
    def _claim_batch(self):
        """Reserva un lote de mensajes de forma atomica.

        SKIP LOCKED + commit inmediato: con max_cron_threads=2 y 5 workers,
        dos procesos pueden entrar a la vez y sin esto se enviaria duplicado.
        """
        ids = self._select_batch_ids()
        if not ids:
            return self.browse()
        messages = self.sudo().browse(ids)
        messages.write({"state": "sending"})
        self.env.cr.commit()  # libera el lock: el HTTP no debe retener filas
        return messages

    # ------------------------------------------------------------------
    # Envio
    # ------------------------------------------------------------------
    def _send_now(self):
        """Hace el POST real a la Bot API. Delega al metodo especifico por tipo."""
        self.ensure_one()
        token = self.env["md.telegram.channel"].sudo()._get_bot_token()
        if not token:
            return self._register_failure(
                _("No hay Bot Token configurado (Ajustes > Telegram)."), permanent=True
            )

        msg_type = self.message_type or "text"
        method = API_METHOD_MAP.get(msg_type, "sendMessage")
        url = API_URL % {"token": token, "method": method}

        if msg_type == "text":
            return self._send_text(url)
        else:
            return self._send_media(url, msg_type)

    def _build_common_payload(self):
        """Construye el payload base que comparten todos los tipos de mensaje."""
        payload = {"chat_id": self.chat_id}
        if self.message_thread_id:
            payload["message_thread_id"] = self.message_thread_id
        if self.disable_notification:
            payload["disable_notification"] = True
        if self.protect_content:
            payload["protect_content"] = True
        if self.reply_markup:
            try:
                payload["reply_markup"] = json.loads(self.reply_markup)
            except (json.JSONDecodeError, TypeError):
                _logger.warning(
                    "Telegram: reply_markup invalido en mensaje id=%s, se ignora.", self.id
                )
        return payload

    def _send_text(self, url):
        """Envia un mensaje de texto plano o HTML/Markdown."""
        payload = self._build_common_payload()
        payload["text"] = self.body
        payload["disable_web_page_preview"] = True
        if self.parse_mode != "none":
            payload["parse_mode"] = self.parse_mode
        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            return self._register_failure(_("Error de red: %s", exc))
        return self._handle_response(response)

    def _send_media(self, url, msg_type):
        """Envia foto, documento, audio o video.

        Telegram acepta el archivo como:
          - URL publica directa (se la pasa a Telegram, el servidor la descarga).
          - file_id previamente subido (mas rapido, no consume ancho de banda).
        El campo media_url puede ser cualquiera de los dos.
        """
        self.ensure_one()
        if not self.media_url:
            return self._register_failure(
                _("Mensaje multimedia sin media_url: falta la URL o file_id del archivo."),
                permanent=True,
            )

        # La clave del payload varia segun el tipo: photo -> 'photo', document -> 'document', etc.
        payload = self._build_common_payload()
        payload[msg_type] = self.media_url

        # Para multimedia el texto va como caption (max 1024).
        if self.body:
            payload["caption"] = self.body
            if self.parse_mode != "none":
                payload["parse_mode"] = self.parse_mode

        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            return self._register_failure(_("Error de red: %s", exc))
        return self._handle_response(response)

    def _handle_response(self, response):
        self.ensure_one()
        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code == 200 and data.get("ok"):
            self.write(
                {
                    "state": "sent",
                    "attempts": self.attempts + 1,
                    "sent_date": fields.Datetime.now(),
                    "error_message": False,
                    "telegram_message_id": str((data.get("result") or {}).get("message_id") or ""),
                }
            )
            return True

        description = data.get("description") or response.text[:500]
        error = _("HTTP %(code)s: %(desc)s", code=response.status_code, desc=description)
        parameters = data.get("parameters") or {}

        if response.status_code == 429:
            retry_after = int(parameters.get("retry_after") or 60)
            return self._register_failure(error, retry_after=retry_after)

        if parameters.get("migrate_to_chat_id"):
            self._migrate_chat(str(parameters["migrate_to_chat_id"]))
            return self._register_failure(error, retry_after=0)

        if response.status_code == 403 and any(
            marker in (description or "").lower() for marker in KICKED_MARKERS
        ):
            self._deactivate_channel(description)
            return self._register_failure(error, permanent=True)

        permanent = response.status_code in PERMANENT_ERROR_CODES
        return self._register_failure(error, permanent=permanent)

    def _migrate_chat(self, new_chat_id):
        """Adopta el nuevo chat_id tras una migracion a supergrupo."""
        self.ensure_one()
        old_chat_id = self.chat_id
        channel = self.channel_id.sudo()
        _logger.warning(
            "Telegram: el grupo %s migro a supergrupo %s; actualizando el canal %r",
            old_chat_id, new_chat_id, channel.name,
        )
        channel.write({"chat_id": new_chat_id})
        pending = self.sudo().search(
            [("chat_id", "=", old_chat_id), ("state", "in", ("pending", "sending"))]
        )
        pending.write({"chat_id": new_chat_id})

    def _deactivate_channel(self, description):
        """Archiva el canal cuyo bot fue expulsado o bloqueado."""
        self.ensure_one()
        channel = self.channel_id.sudo()
        if not channel.active:
            return
        _logger.error(
            "Telegram: canal %r (chat %s) desactivado, el bot ya no puede escribir: %s",
            channel.name, self.chat_id, description,
        )
        channel.write({"active": False})

    def _register_failure(self, error, permanent=False, retry_after=None):
        """Marca el intento fallido y decide si habra reintento."""
        self.ensure_one()
        attempts = self.attempts + 1
        vals = {"attempts": attempts, "error_message": error}

        if permanent or attempts >= MAX_ATTEMPTS:
            vals["state"] = "failed"
            _logger.error(
                "Telegram: envio fallido definitivo id=%s chat=%s (%s intentos): %s",
                self.id, self.chat_id, attempts, error,
            )
        else:
            index = min(attempts - 1, len(BACKOFF_SECONDS) - 1)
            delay = retry_after if retry_after is not None else BACKOFF_SECONDS[index]
            vals["state"] = "pending"
            vals["next_attempt"] = fields.Datetime.now() + timedelta(seconds=delay)
            _logger.warning(
                "Telegram: intento %s/%s fallido id=%s, reintento en %ss: %s",
                attempts, MAX_ATTEMPTS, self.id, delay, error,
            )
        self.write(vals)
        return False

    # ------------------------------------------------------------------
    # Acciones de usuario
    # ------------------------------------------------------------------
    def action_retry(self):
        """Reencola mensajes fallidos desde la vista lista."""
        self.filtered(lambda m: m.state in ("failed", "cancelled")).write(
            {"state": "pending", "attempts": 0, "next_attempt": fields.Datetime.now(), "error_message": False}
        )
        return True

    def action_cancel(self):
        self.filtered(lambda m: m.state in ("pending", "failed")).write({"state": "cancelled"})
        return True

    def action_send_now(self):
        """Fuerza el envio inmediato (sincrono) de un mensaje concreto."""
        for message in self:
            if message.state == "sent":
                raise UserError(_("El mensaje ya fue enviado."))
            message.write({"state": "sending"})
            message._send_now()
            if message.state == "failed":
                raise UserError(_("Fallo el envio: %s", message.error_message))
        return True
