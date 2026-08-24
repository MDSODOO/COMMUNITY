# Plan de Expansión — md_telegram_notify v2.0.0

**Generado:** 2026-08-10  
**Proyecto:** MedicineDepot Sureste — Odoo 19.0  
**Módulo:** `/opt/medicinedepot-odoo19-migration/custom_addons/md_telegram_notify`

---

## 1. Estado anterior (v1.0.0) — Diagnóstico

### Arquitectura
- **Cola asíncrona** robusta: INSERT en `md.telegram.message` + cron de despacho cada 1 min.
- **Backoff exponencial** y respeto del `retry_after` 429 de Telegram.
- **Auto-migración** de chat_id cuando un grupo pasa a supergrupo.
- **Desactivación automática** de canal si el bot es expulsado.

### Funcionalidades cubiertas (v1.0.0)
| Feature | Estado |
|---------|--------|
| Envío de texto (HTML/MarkdownV2) | ✅ |
| Cola DB con retry/backoff | ✅ |
| Multi-canal por código | ✅ |
| Alerta de compra de alto valor | ✅ |
| Thread ID para grupos con temas | ✅ |
| Detección automática de chats | ✅ |

### Limitaciones identificadas (v1.0.0)
| Limitación | Impacto |
|------------|---------|
| Solo 1 trigger (compras) | No hay visibilidad de ventas ni inventario |
| Sin multimedia (fotos/docs) | No se pueden enviar gráficos ni PDFs |
| Sin InlineKeyboard/botones | Mensajes sin acciones directas |
| Sin diagnóstico de webhook | Difícil debuggear conflictos polling/webhook |
| Sin alertas de stock mínimo | Stock bajo pasa desapercibido |
| Sin alertas de ventas | No hay notificación de ventas confirmadas |
| Umbral de ventas no configurable | - |

---

## 2. Mejoras implementadas (v2.0.0)

### 2.1 Soporte Multimedia (sendPhoto, sendDocument, sendAudio, sendVideo)

**Archivo:** `models/telegram_message.py`

```python
# Nuevos campos
message_type = Selection([text, photo, document, audio, video])
media_url = Char  # URL pública o file_id de Telegram
reply_markup = Text  # JSON de InlineKeyboardMarkup
disable_notification = Boolean
protect_content = Boolean

# Nuevos métodos
_send_text(url)    → POST sendMessage
_send_media(url, type) → POST sendPhoto|sendDocument|...
_build_common_payload() → payload base compartido
```

**Uso desde cualquier modelo:**
```python
# Foto con botón
order.telegram_notify_photo(
    url='https://servidor/grafico_ventas.png',
    caption='<b>Ventas del día</b>',
    channel_code='ventas',
    reply_markup={'inline_keyboard': [[{'text': 'Ver Odoo', 'url': order_url}]]}
)
```

### 2.2 InlineKeyboard / Botones (reply_markup)

Cualquier mensaje puede incluir botones inline:

```python
record.telegram_notify_with_buttons(
    body='<b>Aprobación requerida</b>\nOrden: %s' % order.name,
    buttons=[[
        {'text': '✅ Ver en Odoo', 'url': 'https://odoo.../order/123'},
        {'text': '📊 Dashboard', 'url': 'https://odoo.../reports'},
    ]],
    channel_code='operaciones',
)
```

### 2.3 Nuevo trigger: Ventas (sale.order)

**Archivo:** `models/sale_order.py`

- Hereda `action_confirm()` de `sale.order`
- Solo notifica si `amount_total >= md_telegram.sale_threshold`
- Notifica solo canales con `notify_on_sale = True`
- Incluye botón "Ver en Odoo" con URL de la orden

### 2.4 Nuevo trigger: Stock bajo mínimo (stock.quant)

**Archivo:** `models/stock_quant.py`

- Cron diario a las 08:00 UTC
- Compara `qty_available` vs `product_min_qty` en orderpoints activos
- Genera **digest consolidado** (1 mensaje con todos los productos bajos)
- Solo notifica canales con `notify_on_stock_alert = True`
- Evita spam: 1 mensaje/día por canal

### 2.5 Diagnóstico de Webhook

**Método:** `MdTelegramChannel.action_webhook_info()`

- Consulta `getWebhookInfo` de la Bot API
- Muestra URL registrada, errores, updates pendientes
- Ayuda a diagnosticar conflictos polling vs webhook

### 2.6 Prueba multimedia integrada

**Método:** `MdTelegramChannel.action_test_photo()`

- Envía foto de prueba (logo de Telegram) con InlineKeyboard
- Verifica que la integración multimedia funciona end-to-end
- Accesible desde la vista de canal y desde la lista

### 2.7 Configuración por canal

Nuevos campos en `md.telegram.channel`:
- `notify_on_sale` — activa alertas de ventas en este canal
- `notify_on_stock_alert` — activa digest de stock mínimo
- `notify_on_lot_expiry` — activa alertas de caducidad (Fase 3)

---

## 3. Arquitectura v2.0.0

```
Odoo Models
    │
    ├── sale.order.action_confirm()
    │       └── _md_telegram_notify_sale()
    │               └── md.telegram.message.enqueue(type='text', reply_markup=...)
    │
    ├── purchase.order.button_confirm()
    │       └── _md_telegram_notify_high_value()
    │               └── md.telegram.message.enqueue(type='text')
    │
    ├── stock.quant._cron_telegram_low_stock() [cron 08:00 UTC]
    │       └── md.telegram.message.enqueue(type='text', body=digest)
    │
    └── base.telegram_notify_photo(url, caption, ...)
            └── md.telegram.message.enqueue(type='photo', media_url=..., reply_markup=...)

md.telegram.message (Cola DB)
    │
    └── _cron_dispatch() [cada 1 min]
            ├── _send_text() → POST /sendMessage
            ├── _send_media() → POST /sendPhoto|sendDocument|...
            └── _handle_response() → retry/backoff/deactivate
```

---

## 4. Roadmap — Fases futuras

### Fase 3: Alertas de caducidad de lotes (md_lots_management)
- Hereda `stock.lot`
- Cron diario: busca lotes con `expiration_date <= today + 30 days`
- Digest consolidado agrupado por días restantes
- Canal configurable via `notify_on_lot_expiry`

### Fase 4: Webhook entrante (comandos del bot)
- Controller HTTP en Odoo que recibe updates de Telegram
- Router de comandos: `/status`, `/ventas`, `/stock`, `/pedidos`
- Respuestas automáticas con datos en tiempo real de Odoo

### Fase 5: Integración con local_ai_connector
- Enriquecer mensajes con análisis de IA (Ollama)
- Resúmenes automáticos de tendencias de ventas
- Alertas contextualizadas: "Las ventas de Paracetamol bajaron 40% esta semana"

### Fase 6: Dashboard de métricas Telegram
- Vista kanban de canales con estadísticas de entrega
- Tasa de éxito, tiempo promedio de entrega, errores por canal
- Integración con el módulo de reportes existente

---

## 5. Configuración post-upgrade

```bash
# 1. Actualizar módulo en Odoo (si es upgrade desde v1)
docker exec medicinedepot_dev_odoo odoo --update md_telegram_notify --stop-after-init -d medicinedepot_dev

# 2. En Ajustes > Telegram, configurar:
#    - Umbral de alerta en ventas (ej: 5000)
#    
# 3. En cada canal, activar las alertas deseadas:
#    - notify_on_sale: canales de ventas
#    - notify_on_stock_alert: canales de inventario

# 4. Probar con el botón "Probar foto + botones" en la vista de canal
```

---

## 6. Archivos modificados/creados

| Archivo | Tipo | Cambio |
|---------|------|--------|
| `models/base_telegram.py` | Modificado | +telegram_notify_photo(), +telegram_notify_document(), +telegram_notify_with_buttons() |
| `models/telegram_message.py` | Modificado | +message_type, +media_url, +reply_markup, +_send_media(), +API_METHOD_MAP |
| `models/telegram_channel.py` | Modificado | +notify_on_sale, +notify_on_stock_alert, +notify_on_lot_expiry, +send_photo(), +send_document(), +action_webhook_info(), +action_test_photo() |
| `models/res_config_settings.py` | Modificado | +md_telegram_sale_threshold, +action_md_telegram_webhook_info() |
| `models/purchase_order.py` | Sin cambios | - |
| `models/sale_order.py` | **NUEVO** | Alertas de ventas confirmadas con botón "Ver en Odoo" |
| `models/stock_quant.py` | **NUEVO** | Digest diario de stock bajo punto de reorden |
| `models/__init__.py` | Modificado | Importar sale_order, stock_quant |
| `__manifest__.py` | Modificado | v2.0.0, +sale_management, +stock en depends |
| `data/telegram_data.xml` | Modificado | +param_sale_threshold |
| `data/ir_cron_stock.xml` | **NUEVO** | Cron diario stock mínimo |
| `views/telegram_channel_views.xml` | Modificado | +campos notify_*, +botones de prueba multimedia |

**Total: 9 Python ✅ + 6 XML ✅ — Sin errores de sintaxis**
