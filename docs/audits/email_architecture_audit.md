# Auditoría de Correo Electrónico — Odoo 19

## 1. Resumen Ejecutivo

| Aspecto | Estado |
|---|---|
| **SMTP saliente** | Configurado en BD (`ir_mail_server`) pero **100% fallido** — 1,077 correos en estado `exception` |
| **IMAP entrante** | Configurado (`fetchmail_server`, `mail.medicinedepotsureste.mx:993`) pero **sin integración real** |
| **ICP requeridos** | `mail.catchall.domain` y `mail.default.from` **ausentes** — causa raíz de fallos recientes |
| **Plantillas email** | 0 `mail.template` en módulos custom |
| **`mail.thread`** | 2 modelos custom lo heredan (pharmacovigilance, AI quote request) |
| **Chatter** | 1 vista custom con `<chatter/>` explícito |
| **Cliente correo custom** | `md_mail_client` — Gmail-like sobre `mail.mail` (solo saliente) |

## 2. Arquitectura Actual

### 2.1. Servidores de Correo

**Saliente (SMTP)**
```
Host: mail.medicinedepotsureste.mx:465 (SSL)
Usuario: odoo@medicinedepotsureste.mx
Activo: Sí
```

**Entrante (IMAP)**
```
Host: mail.medicinedepotsureste.mx:993 (SSL)
Estado: done (última ejecución completada)
```

### 2.2. Parámetros Faltantes (Causa Raíz #1)

```sql
-- NO existen en ir_config_parameter:
mail.catchall.domain      → debería ser "medicinedepotsureste.mx"
mail.default.from          → debería ser "odoo@medicinedepotsureste.mx"
mail.bounce.alias          → no configurado
mail.catchall.alias        → no configurado
```

Esto provoca el error:
> *"You must either provide a sender address explicitly or configure using the combination of `mail.catchall.domain` and `mail.default.from` ICPs"*

### 2.3. Fallo SMTP Adicional (Causa Raíz #2)

Los registros antiguos muestran `Connection refused (111)` — el contenedor Odoo no puede alcanzar `mail.medicinedepotsureste.mx:465`. Posibles causas:
- Firewall del servidor/cPanel bloquea la IP del servidor Odoo
- El puerto 465 requiere autenticación adicional o IP permitida en cPanel
- El contenedor Docker no tiene resolución DNS o conectividad saliente al puerto 465

## 3. Flujo de Correo Actual

### 3.1. Envío de Correo (Flujo Saliente)

```
Evento de negocio (ej. validar sesión POS, crear factura)
  └→ mail.mail.create() [generalmente con sudo()]
      └→ mail.mail.send()
          └→ ir.mail_server.send_email()  ← FALLA: Connection refused / sin default_from
              └→ mail.mail.state = 'exception'
                  └→ failure_reason = "Connection refused" o "missing sender"
```

**Puntos de envío identificados:**
1. `bi_pos_stock/models/pos_z_report.py:55` — `mail.mail.sudo().create({...}).send()`
2. `bi_pos_stock/models/pos_z_report.py:85` — Preview email via `mail.mail.sudo().create({...}).send()`
3. Odoo core: facturas, órdenes de venta, notificaciones (todos fallan)

### 3.2. Chatter / Message Post (Flujo Interno — Sí Funciona)

```
Model.method()
  └→ record.message_post(body=..., subtype_xmlid=...)
      └→ mail.message.create()
          └→ mail.thread._message_log()  ← SOLO base de datos, NO envía email
```

**Puntos de `message_post` identificados:**
1. `pos_z_report.py:65` — "Reporte Z enviado a X" en chatter de sesión POS
2. `pos_z_report.py:94` — Preview enviada en chatter de sesión POS
3. `purchase_invoice_parser/services/purchase_order_builder.py:258` — CFDI metadata en chatter de PO
4. `purchase_invoice_parser/models/purchase_invoice_import_wizard.py:1459` — Price change en chatter de producto
5. `md_lots_management/models/production_lot.py:259` — Histórico de cambios en chatter de lote
6. `local_ai_connector/models/image_quote_request.py:166` — Cotización creada en chatter de SO

### 3.3. Cliente de Correo Custom (`md_mail_client`)

- **Propósito:** Bandeja tipo Gmail sobre `mail.mail` (sin depender de `web_enterprise`)
- **Estado:** Funcional en UI pero solo muestra correos **salientes** (`mail.mail`)
- **Limitación:** Las carpetas "Recibidos" y "Enviados" están etiquetadas con:
  > *"Los folders 'Recibidos'/'Enviados' se llenarán cuando conectemos el servidor IMAP/SMTP"*
- **Sincronización:** Usa `bus_service` → `mail.record/insert` para refrescar en tiempo real

### 3.4. Notificaciones Reales (Bus — Sí Funcionan)

Los eventos `bus.bus` para el POS y cambios de precio funcionan correctamente:
- `ECOMMERCE_ORDER` → POS sessions (bi_pos_stock)
- `BRANCH_STOCK_UPDATED` → POS sessions (bi_pos_stock)
- `purchase_invoice_parser/price_update` → UI de notificaciones (purchase_invoice_parser)

## 4. Modelos con `mail.thread`

| Modelo | Módulo | Chatter Activo |
|---|---|---|
| `medicine.depot.pharmacovigilance.report` | `medicine_depot_portal` | ✅ Vista form con `<chatter/>` |
| `local.ai.image.quote.request` | `local_ai_connector` | ✅ Hereda `mail.thread` |

## 5. Configuración Relacionada

### 5.1. `sale.async_emails = False`
Los correos de ventas NO se envían de forma asíncrona — se intentan enviar sincrónicamente durante la confirmación.

### 5.2. `mail_notify_force_send = False`
Inyectado por `sale_account_custom/models/ir_actions_server.py` para evitar que server actions disparen correos inmediatamente.

### 5.3. `base.default_max_email_size = 10` (MB)
Tamaño máximo de adjuntos en correos salientes.

## 6. Diagnóstico Técnico

### Problema 1: Ausencia de `mail.catchall.domain` y `mail.default.from`
**Solución:** Agregar vía UI (Ajustes → Técnico → Parámetros del Sistema) o SQL:
```sql
INSERT INTO ir_config_parameter (key, value) VALUES
  ('mail.catchall.domain', 'medicinedepotsureste.mx'),
  ('mail.default.from', 'odoo@medicinedepotsureste.mx');
```

### Problema 2: Connection refused (111) al SMTP
**Diagnóstico:** El contenedor Odoo no puede conectar a `mail.medicinedepotsureste.mx:465`
**Verificar:**
```bash
# Desde el host
nc -zv mail.medicinedepotsureste.mx 465

# Desde el contenedor
docker exec medicinedepot_dev_odoo nc -zv mail.medicinedepotsureste.mx 465
```

### Problema 3: 1,077 correos en exception sin reprocesar
**Solución:** Reprocesar cola tras corregir configuración:
```python
self.env['mail.mail'].search([('state', '=', 'exception')]).send()
```

## 7. Recomendaciones Prioritarias

1. **Configurar ICPs** `mail.catchall.domain` y `mail.default.from`
2. **Diagnosticar conectividad SMTP** desde contenedor Docker al puerto 465
3. **Reprocesar cola** de correos fallidos
4. **Agregar monitoreo** al estado de `mail.mail` (alerta si hay registros en exception)
5. **Completar `md_mail_client`** con integración IMAP real
6. **Estandarizar** el uso de `mail.template` en vez de `ir.qweb._render()` manual
