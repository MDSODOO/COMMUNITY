# Auditoría: Integración Correo ↔ Parser de Facturas CFDI — Medicine Depot

**Fecha:** 2026-08-10
**Alcance real auditado:** `md_mail_client`, `md_mail_accounts`, `purchase_invoice_parser` (Odoo 19, `custom_addons/`)
**Método:** lectura directa del código fuente de los 3 módulos (no solo README/CHANGELOG), verificado línea por línea en los puntos críticos.

## ⚠️ Corrección al punto de partida

El goal pedía auditar la integración entre `md_mail_client` y `purchase_invoice_parser`. Verificado en código: **esa integración no existe, ni a nivel de dependencias del manifest ni a nivel de una sola línea de código.**

- `md_mail_client` (`depends: ['mail', 'web']`) es **puramente UI**: una bandeja estilo Gmail sobre `mail.mail`. No tiene carpeta `models/`, cero lógica Python propia de negocio.
- `purchase_invoice_parser` (`depends: ['purchase', 'stock', 'mail', 'bus', 'md_product_lines']`) es un **wizard manual**: el usuario sube XML/PDF/ZIP a mano desde Compras → Órdenes de Compra → "Importar XML". No tiene ninguna referencia a `mail.mail`, `fetchmail`, `md_mail_client` ni a procesamiento de correo entrante en ninguno de sus ~20 archivos Python.
- El módulo que **sí** descarga correo automáticamente es un tercero que el goal no mencionó: **`md_mail_accounts`** (`depends: ['mail', 'md_mail_client']`) — credenciales IMAP/SMTP por usuario, cron cada 5 min, crea `mail.mail`.

**Por lo tanto, el "flujo AS-IS" real no es un puente roto entre dos módulos — es la ausencia total de un puente**, y el motivo concreto (no especulativo, verificado abajo) es más específico y más fácil de arreglar de lo que el planteamiento original asumía.

---

## Hallazgo principal: los adjuntos se descartan en la descarga IMAP

En `md_mail_accounts/models/mail_account.py`, el método `fetch_mails()` → `_email_to_mail_values()` → `_get_body_html()`:

```python
def _get_body_html(self, email_message):
    if email_message.is_multipart():
        html_part = None
        text_part = None
        for part in email_message.walk():
            ctype = part.get_content_type()
            if ctype == 'text/html' and not html_part:
                html_part = part
            elif ctype == 'text/plain' and not text_part:
                text_part = part
            ...
```

Este método camina el árbol MIME del correo **buscando únicamente `text/html` o `text/plain`**. No hay ninguna rama que detecte `Content-Disposition: attachment`, ni código que llame a `ir.attachment.create()` con los bytes de un adjunto. El `mail.mail` resultante se crea solo con `subject`, `email_from`, `email_to`, `body_html`, `date` — **el PDF/XML/ZIP de la factura nunca llega a la base de datos de Odoo**, se descarta en el momento del fetch IMAP y no queda ningún rastro de que existió.

Esto explica por completo por qué el flujo hoy es 100% manual: aunque se construyera un disparador automático desde `md_mail_client` hacia `purchase_invoice_parser`, no habría nada que pasarle — el archivo ya se perdió tres pasos antes.

**Cómo se procesan las facturas hoy, en la práctica:** alguien revisa su correo real (Gmail/Outlook, no `md_mail_client`, porque ahí no hay adjunto), descarga el XML/PDF a su computadora, y lo sube manualmente al wizard. `md_mail_client`/`md_mail_accounts` quedan como un visor de "recibidos" que nunca se usa para este flujo en particular.

---

## Mapeo del flujo AS-IS (real, verificado)

```
Proveedor envía correo con XML+PDF/ZIP
        │
        ▼
Servidor IMAP (mail.medicinedepotsureste.mx)
        │
        ▼
md_mail_accounts: cron cada 5 min → fetch_mails()
   ├─ IMAP search UNSEEN (sin límite de cantidad)
   ├─ por cada mensaje: extrae solo texto/HTML
   ├─ ❌ adjuntos descartados aquí
   └─ crea mail.mail (state='received')
        │
        ▼
md_mail_client: usuario ve el correo en su bandeja
   └─ sin adjunto visible/descargable (nunca se guardó)
        │
        ▼
[GAP — proceso 100% humano, fuera de Odoo]
Usuario va a su correo real, descarga XML/PDF a su PC
        │
        ▼
purchase_invoice_parser: usuario abre wizard manualmente
   ├─ sube XML (+ PDF/ZIP opcional)
   ├─ CFDIParser.parse_bytes() — parseo maduro, con
   │  extractores dedicados por RFC (BRUDIFARMA, QUIFAMESA)
   ├─ SupplierMatcher.find_partner() — RFC exacto → parcial → nombre
   ├─ ProductMatcher.find_product()
   └─ usuario revisa y confirma → crea purchase.order
```

### Debilidades identificadas (verificadas en código, no supuestas)

| # | Debilidad | Módulo | Evidencia |
|---|---|---|---|
| 1 | Adjuntos descartados en el fetch IMAP | `md_mail_accounts` | `_get_body_html()` solo extrae text/html/plain |
| 2 | Credenciales IMAP/SMTP en texto plano | `md_mail_accounts` | `imap_password = fields.Char(...)` — el manifest dice "cifradas en BD", el código no cifra nada |
| 3 | Cron secuencial, sin paralelismo ni límite por cuenta | `md_mail_accounts` | `_cron_fetch_all` itera `for account in accounts` sin threads ni batch |
| 4 | Sin límite en `UNSEEN` — una cuenta caída semanas puede saturar un solo run | `md_mail_accounts` | `conn.search(None, 'UNSEEN')` sin paginar |
| 5 | Auto-creación de `res.partner` sin validación al primer correo de un remitente desconocido | `md_mail_accounts` | `_resolve_sender_partner()` crea partner con solo nombre+email, sin dedup — mismo patrón que causó los proveedores duplicados que se limpiaron hoy en `medicinedepot_dev` (Quifamesa/Brudifarma) |
| 6 | Sin alerta proactiva al usuario cuando una cuenta entra en `state='error'` | `md_mail_accounts` | `error_message`/`error_date` se guardan pero nada notifica; `action_clear_error` es reactivo |
| 7 | `SupplierMatcher.find_partner()` sin `order` explícito en `search()` | `purchase_invoice_parser` | Misma clase de bug que se encontró y corrigió hoy en el workflow n8n `04_Sync_Ordenes_Compra` — con proveedores duplicados, `limit=1` sin orden cae en orden alfabético por defecto, no en el registro correcto |
| 8 | Sin validación de XML contra el XSD oficial del SAT | `purchase_invoice_parser` | `CFDIParser` solo valida bien-formado + presencia de campos clave, no el esquema completo |
| 9 | Sin trazabilidad correo → OC | `purchase_invoice_parser` | Ya reconocido en su propio README ("Extensiones Sugeridas #4"): no hay campo que ligue el origen del CFDI a la OC creada |
| 10 | `action_export_excel` sin verificación de permisos | `purchase_invoice_parser` | Ya identificado en auditoría previa del módulo (2026-06-27), sigue sin corregir |

---

## Nota de reconciliación con el trabajo de hoy (n8n + OCR)

Antes de proponer más automatización, vale decirlo con franqueza: **`purchase_invoice_parser` ya hace, de forma más madura, buena parte de lo que construí hoy en el sidecar OCR de n8n.** `CFDIParser` tiene extractores dedicados por RFC para `BRU971010227` (Brudifarma) y `QFM861010BL0` (Quifamesa) — los mismos dos proveedores con los que probé el pipeline de OCR —, maneja IVA/IEPS/retenciones, lotes embebidos en la Descripción (formato Brudifarma) y Addendas, con 135 commits de historial y suite de tests. Mi extracción por regex sobre imágenes con Tesseract es razonable para *documentos que no traen XML*, pero para CFDI con XML —que es el caso de Quifamesa y Brudifarma, según confirmaste— este parser nativo es la vía correcta, no el OCR. Recomendación concreta: el sidecar OCR debería reposicionarse como *fallback* para PDFs escaneados sin XML, no como camino principal.

---

## Plan de mejoras (13 puntos accionables)

### a) Mapeo AS-IS y debilidades
*(cubierto arriba — 10 debilidades verificadas en código)*

### b) Optimización de descarga y lectura de correos

1. **Extraer y persistir adjuntos en el fetch IMAP** (la mejora que de verdad destraba todo lo demás): en `_email_to_mail_values`, caminar `email_message.walk()` buscando partes con `Content-Disposition: attachment` (o `inline` con filename), y crear `ir.attachment` ligados al `mail.mail` resultante vía `res_model='mail.mail', res_id=mail.id`. Sin esto, cualquier automatización posterior no tiene qué procesar.
2. **Paralelizar `_cron_fetch_all`** con `ThreadPoolExecutor` (cada cuenta IMAP es independiente, no hay razón para procesarlas en serie) — impacto directo si el número de cuentas de usuario crece.
3. **Acotar `UNSEEN` con límite por corrida** (ej. `conn.search(None, 'UNSEEN')` + procesar máx. 50 por cuenta por ciclo, dejar el resto para el siguiente cron de 5 min) para que una cuenta caída mucho tiempo no bloquee ni retrase a las demás.
4. **Cifrar `imap_password`/`smtp_password` de verdad**, ya sea con un campo tipo `fields.Char(groups='base.group_system')` + almacenamiento cifrado (ej. vía `cryptography.Fernet` con clave en variable de entorno, no en la BD), para que el manifest deje de describir una garantía que el código no cumple.

### c) Precisión del parser

5. **Cerrar el gap real**: una vez que (1) exista, agregar una acción (botón o cron) que tome adjuntos XML/ZIP nuevos en `mail.mail` y los pre-cargue en `purchase.invoice.import.wizard` — puede ser tan simple como un botón "Importar desde este correo" en la vista de `md_mail_client`, sin necesitar automatización total de entrada.
6. **Validar XML contra el XSD 4.0 del SAT** (`lxml.etree.XMLSchema`) antes de aceptar un CFDI, no solo verificar bien-formado — atraparía facturas corruptas o de proveedores con CFDI mal generado antes de intentar crear una OC con datos parciales.
7. **Reservar el sidecar OCR (n8n) para el caso sin XML**: documentos que llegan solo como imagen/PDF escaneado sin el XML acompañante. No competir con `CFDIParser` en el caso CFDI+XML, que ya está resuelto.
8. **Corregir `SupplierMatcher.find_partner()` para ordenar explícitamente** (`order='supplier_rank desc'`) igual que se hizo hoy en el workflow n8n — mismo bug, mismo fix, evita que un proveedor recién duplicado (por el punto #9 de auto-creación) rompa el matching silenciosamente.

### d) Experiencia de usuario / alertas

9. **Validar duplicados antes de auto-crear `res.partner` en `_resolve_sender_partner`**: buscar también por nombre similar (`ilike`) antes de crear, y si hay ambigüedad, dejar el correo sin partner asignado en vez de crear uno nuevo a ciegas — evita repetir el mismo problema de proveedores duplicados que se limpió hoy en `medicinedepot_dev`.
10. **Notificación proactiva cuando una cuenta de correo entra en error**: hoy `state='error'` es silencioso hasta que alguien entra a revisar. Usar el mismo patrón de bus/toast que ya existe en `purchase_invoice_parser` (`_notify_price_changes`) para avisar en tiempo real al usuario dueño de la cuenta.
11. **Alerta cuando un XML falla el parseo o no matchea proveedor/producto**: hoy el wizard muestra `parse_warnings`/confianza baja solo si el usuario está mirando la pantalla en ese momento; agregar una actividad (`mail.activity`) asignada al usuario cuando `partner_confidence < 0.7` o `parse_errors` no está vacío, para que no se pierda si cierran el wizard sin terminar.
12. **Trazabilidad correo → OC**: agregar campo `source_mail_id` (Many2one a `mail.mail`) en `purchase.order`, poblado automáticamente cuando la importación se originó desde un adjunto de correo (una vez implementado el punto #5) — cierra el gap ya reconocido en el propio README del parser.
13. **Corregir el permiso faltante en `action_export_excel`** (hallazgo de la auditoría previa del módulo, 2026-06-27, aún sin resolver) — verificación de grupo antes de exportar datos de precios/proveedores.

---

## Priorización sugerida

1. **Primero (destraba todo lo demás):** punto b1 — extraer adjuntos. Sin esto, ninguna automatización tiene sentido.
2. **Segundo (seguridad, bajo esfuerzo):** b4 (cifrado de credenciales) y d13 (permiso faltante) — ambos ya identificados, solo falta implementarlos.
3. **Tercero (cierra el círculo):** c5 (botón importar-desde-correo) + d12 (trazabilidad) — convierte el hallazgo #1 en valor real para el usuario.
4. **Cuarto (robustez):** b2/b3 (paralelismo y límites de cron), c8 (orden explícito en matching), d9/d10/d11 (validaciones y alertas).
5. **Quinto (calidad fiscal):** c6 (validación XSD).
