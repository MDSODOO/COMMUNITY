{
    'name': 'MDS — Notificaciones por Telegram',
    'version': '19.0.2.0.0',
    'category': 'Tools',
    'summary': 'Alertas automaticas de Odoo a grupos y canales de Telegram (cola asincrona)',
    'description': """
Envia alertas desde Odoo a Telegram sin acoplar la API externa a las
transacciones de negocio.

- Bot Token en ir.config_parameter (lectura restringida a Administracion).
- Canales de destino como registros (md.telegram.channel), varios chat_id.
- Cola en base de datos + cron: el trigger solo hace INSERT, el POST HTTP
  ocurre en otra transaccion. Telegram caido nunca bloquea ni revierte una
  operacion de Odoo.
- Reintentos con backoff exponencial, respeto del retry_after de la API (429)
  y descarte de errores permanentes (token invalido, bot expulsado).

=== Fase 2 (2026-08): Soporte multimedia y nuevos triggers ===
- Mensajes con fotos, documentos, audio y video (sendPhoto, sendDocument...).
- Botones interactivos (InlineKeyboardMarkup) en cualquier mensaje.
- Nuevos shortcuts en todos los modelos:
    record.telegram_notify_photo(url, caption, channel_code='ventas')
    record.telegram_notify_with_buttons(body, buttons, channel_code='ops')
- Alertas de ventas confirmadas (sale.order) con boton 'Ver en Odoo'.
- Digest diario de stock bajo punto de reorden (stock.quant via orderpoints).
- Configuracion por canal: notify_on_sale, notify_on_stock_alert.
- Diagnostico de webhook: accion 'Info Webhook' en ajustes.
- Prueba de foto con botones desde la vista de canal.

Uso desde cualquier modelo:
    record.telegram_notify("<b>Algo paso</b>", channel_code="compras")
    record.telegram_notify_photo(url, caption="Reporte", channel_code="ventas")
    record.telegram_notify_with_buttons(body, [[{"text":"Ver","url":"..."}]])
    """,
    'author': 'MedicineDepot Sureste',
    'depends': ['base_setup', 'purchase', 'sale_management', 'stock'],
    'external_dependencies': {'python': ['requests']},
    'data': [
        'security/ir.model.access.csv',
        'data/telegram_data.xml',
        'data/ir_cron.xml',
        'data/ir_cron_stock.xml',
        'views/telegram_channel_views.xml',
        'views/telegram_message_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
