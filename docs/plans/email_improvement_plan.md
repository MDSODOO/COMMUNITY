# Plan de Mejora: Sistema de Correo Electrónico

## Estado Actual

- **SMTP**: Configurado en BD pero 1,077 correos fallidos (Connection refused + missing ICPs)
- **IMAP**: Configurado pero sin integración real con el cliente de correo
- **Chatter**: Funciona correctamente (solo DB, sin enviar emails)
- **Cliente custom**: `md_mail_client` funcional pero solo sobre `mail.mail` (saliente)
- **Plantillas**: 0 `mail.template` en módulos custom

---

## Fase 1: Corrección de Configuración SMTP

### Capa: Configuración / Infraestructura

- [ ] Agregar ICPs faltantes en `ir_config_parameter`:
  - `mail.catchall.domain` → "medicinedepotsureste.mx"
  - `mail.default.from` → "odoo@medicinedepotsureste.mx"
- [ ] Diagnosticar conectividad SMTP desde contenedor Odoo
- [ ] Verificar reglas de firewall/cPanel para IP del servidor
- [ ] Reprocesar cola de correos en estado `exception`
- [ ] Agregar healthcheck que monitoree estado de `mail.mail`

**[ESPERANDO INSTRUCCIONES DEL USUARIO]**

---

## Fase 2: Estandarización de Envío de Correos

### Capa: Modelos / Servicios

- [ ] Crear `mail.template` para Reporte Z farmacéutico (reemplazar `ir.qweb._render()` manual)
- [ ] Centralizar lógica de creación de `mail.mail` en un servicio reusable
- [ ] Agregar `mail_notify_force_send` handling consistente
- [ ] Estandarizar resolución de `email_from` (usar ICP `mail.default.from` en vez de `ir.mail_server._get_default_from_address()`)

**[ESPERANDO INSTRUCCIONES DEL USUARIO]**

---

## Fase 3: Chatter y Mail Thread

### Capa: Modelos / Vistas

- [ ] Agregar `<chatter/>` explícito en vistas form faltantes:
  - `local.ai.image.quote.request` (hereda `mail.thread` pero no tiene chatter en vista)
  - `stock.lot` (ya tiene `message_post` pero vista sin chatter visible)
- [ ] Agregar `tracking=True` a campos críticos en modelos de negocio
- [ ] Unificar `subtype_xmlid` usado en `message_post` en los módulos custom

**[ESPERANDO INSTRUCCIONES DEL USUARIO]**

---

## Fase 4: Integración IMAP en `md_mail_client`

### Capa: Controladores / Frontend

- [ ] Implementar fetching IMAP real (o conector fetchmail) para poblar "Recibidos"
- [ ] Refactorizar dominios de "Recibidos"/"Enviados" para usar datos IMAP reales
- [ ] Agregar sincronización bidireccional (marcar como leído, mover a papelera)
- [ ] Remover hint de UI: *"Los folders se llenarán cuando conectemos IMAP/SMTP"*

**[ESPERANDO INSTRUCCIONES DEL USUARIO]**

---

## Fase 5: Plantillas de Correo y Notificaciones

### Capa: Vistas/Plantillas XML / Modelos

- [ ] Migrar `bi_pos_stock.pharma_z_report_email_body` a `mail.template`
- [ ] Crear `mail.template` para notificaciones de cambio de precio
- [ ] Crear `mail.template` para alertas de farmacovigilancia
- [ ] Agregar diseño responsivo unificado (base email layout)

**[ESPERANDO INSTRUCCIONES DEL USUARIO]**

---

## Fase 6: Monitoreo y Alertas

### Capa: Infraestructura / DevOps

- [ ] Agregar métrica de `mail.mail.state = 'exception'` al healthcheck
- [ ] Alerta si > 10 correos en exception en las últimas 24h
- [ ] Dashboard de estado del servidor SMTP (ping al puerto 465)
- [ ] Cron de reprocesamiento automático de correos fallidos (con backoff)

**[ESPERANDO INSTRUCCIONES DEL USUARIO]**

---

## Fase 7: Tests

### Capa: E2E / Unitarios

- [ ] Test E2E: verificar que `mail.catchall.domain` y `mail.default.from` existen
- [ ] Test E2E: enviar mensaje desde chatter y verificar en BD (mail.message)
- [ ] Test E2E: cliente de correo md_mail_client carga correctamente
- [ ] Test unitario: creación de `mail.mail` con `email_from` resuelto de ICPs
- [ ] Test unitario: resolución de destinatarios en Reporte Z

**[ESPERANDO INSTRUCCIONES DEL USUARIO]**

---

## Árbol de Decisiones

```
¿Corregir SMTP primero?
├── Sí → Fase 1 (ICPs + conectividad)
│   └── ¿Funciona? → Fase 2 (estandarizar envío)
└── No → Saltar a Fase 3 o 4

¿Priorizar UI o backend?
├── Chatter/Thread → Fase 3
├── Cliente correo IMAP → Fase 4
└── Plantillas → Fase 5

¿Requiere monitoreo?
├── Sí → Fase 6
└── No → Omitir
```

---

*Generado el 2026-07-29. Marcar tareas con `[x]` conforme se completen.*
