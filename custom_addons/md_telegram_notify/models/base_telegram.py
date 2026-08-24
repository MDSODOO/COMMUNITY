from odoo import models


class Base(models.AbstractModel):
    """Atajo disponible en TODOS los modelos.

    Permite `record.telegram_notify("...")` desde cualquier sitio: un override
    de Python, una accion de servidor o una accion automatizada, sin tener que
    conocer el modelo de la cola.

    --- Fase 2 (2026-08): soporte multimedia y botones ---
    Se anadieron:
      - telegram_notify_photo(): encola una foto con caption opcional.
      - telegram_notify_document(): encola un documento con caption.
      - telegram_notify_with_buttons(): encola texto con InlineKeyboard.
    """

    _inherit = "base"

    def telegram_notify(self, body, channel_code=None, parse_mode="HTML", thread_id=None):
        """Encola una alerta de Telegram asociada a este registro.

        No hace red: solo encola. Devuelve el/los md.telegram.message creados.
        """
        record = self[:1] if self else None
        return self.env["md.telegram.message"].enqueue(
            body=body,
            channel_code=channel_code,
            record=record,
            parse_mode=parse_mode,
            thread_id=thread_id,
        )

    def telegram_notify_photo(
        self,
        url_or_file_id,
        caption="",
        channel_code=None,
        parse_mode="HTML",
        thread_id=None,
        reply_markup=None,
        disable_notification=False,
    ):
        """Encola una foto de Telegram asociada a este registro.

        :param url_or_file_id: URL publica de la imagen o file_id ya subido.
        :param caption: texto HTML que acompana la foto (max 1024 chars).
        :param reply_markup: dict con InlineKeyboardMarkup u otro markup.

        Uso desde cualquier modelo:
            order.telegram_notify_photo(
                url='https://mi.dominio/grafico.png',
                caption='<b>Grafico de ventas</b>',
                channel_code='ventas',
                reply_markup={'inline_keyboard': [[
                    {'text': 'Ver detalle', 'url': order._get_share_url()}
                ]]},
            )
        """
        record = self[:1] if self else None
        return self.env["md.telegram.message"].enqueue(
            body=caption,
            channel_code=channel_code,
            record=record,
            parse_mode=parse_mode,
            thread_id=thread_id,
            message_type="photo",
            media_url=url_or_file_id,
            reply_markup=reply_markup,
            disable_notification=disable_notification,
        )

    def telegram_notify_document(
        self,
        url_or_file_id,
        caption="",
        channel_code=None,
        parse_mode="HTML",
        thread_id=None,
        reply_markup=None,
    ):
        """Encola un documento (PDF, xlsx...) de Telegram asociado a este registro.

        :param url_or_file_id: URL publica del documento o file_id de Telegram.
        :param caption: texto HTML que acompana el documento (max 1024 chars).
        """
        record = self[:1] if self else None
        return self.env["md.telegram.message"].enqueue(
            body=caption,
            channel_code=channel_code,
            record=record,
            parse_mode=parse_mode,
            thread_id=thread_id,
            message_type="document",
            media_url=url_or_file_id,
            reply_markup=reply_markup,
        )

    def telegram_notify_with_buttons(
        self,
        body,
        buttons,
        channel_code=None,
        parse_mode="HTML",
        thread_id=None,
        disable_notification=False,
    ):
        """Encola un mensaje de texto con botones InlineKeyboard.

        :param body: texto HTML del mensaje.
        :param buttons: lista de listas de botones. Cada boton es un dict con
            'text' y 'url' (o 'callback_data' para callbacks).
            Ejemplo: [[{'text': 'Ver', 'url': 'https://...'}]]
        :param channel_code: codigo del canal destino.

        Uso desde cualquier modelo:
            sale.telegram_notify_with_buttons(
                body='<b>Nueva venta confirmada</b>',
                buttons=[[
                    {'text': 'Ver orden', 'url': sale._get_share_url()},
                    {'text': 'Aprobar', 'callback_data': 'approve_%d' % sale.id},
                ]],
                channel_code='ventas',
            )
        """
        record = self[:1] if self else None
        reply_markup = {"inline_keyboard": buttons}
        return self.env["md.telegram.message"].enqueue(
            body=body,
            channel_code=channel_code,
            record=record,
            parse_mode=parse_mode,
            thread_id=thread_id,
            reply_markup=reply_markup,
            disable_notification=disable_notification,
        )
