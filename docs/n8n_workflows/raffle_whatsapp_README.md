# Notificaciones WhatsApp de Rifas (Odoo → n8n → WhatsApp Cloud API)

**Actualizado (2026-08-14): este camino ya es el oficial.** Existía un envío
directo Odoo→Meta (`_build_whatsapp_payload` / `_send_whatsapp_ticket_update`
en `raffle_campaign.py`, vía el cron `mds_raffle_campaign.ir_cron_whatsapp_...`
en `data/raffle_whatsapp_cron.xml`), pero **ese cron ya venía `active=False`
por defecto y se queda así de forma permanente** — el camino
**Odoo → webhook n8n → WhatsApp Cloud API** lo reemplaza (decisión tomada
para no mantener ni aprobar dos plantillas de Meta para el mismo mensaje).
La llamada real desde Odoo **sí está implementada**: `raffle.ticket.create()`
en `custom_addons/mds_raffle_campaign/models/raffle_ticket.py` dispara
`_notify_n8n_tickets_created()` al final de cada creación de boletos (POS,
sale.order B2B, backfill diario — todos pasan por ese único `create()`),
con un `requests.post()` best-effort a la URL configurada en
Ajustes → Rifas → Automatización (n8n) (`ir.config_parameter`
`mds_raffle_campaign.n8n_webhook_url`). Vacío = no-op, igual que el token
de WhatsApp.

La plantilla de Meta usada por el nodo "Enviar Plantilla WhatsApp" del
Workflow A se alineó a **`raffle_ticket_update`** (el nombre que ya usaba
el código Odoo retirado) en vez de `raffle_new_tickets` — una sola plantilla
que aprobar en Meta Business Manager, con los 4 parámetros posicionales que
ya traía el diseño de n8n (nombre, conteo, folios, campaña — más completo
que los 3 que mandaba el cron retirado).

## Archivos de esta tarea

- `raffle_whatsapp_notify.json` — Workflow A: notifica boletos nuevos.
- `raffle_whatsapp_summary.json` — Workflow B: resumen/recordatorio de cierre.
- `raffle_whatsapp_README.md` — este archivo.

(El `README.md` sin sufijo y `15_alertas_anomalias_cashback.json` de esta
misma carpeta son de un trabajo anterior sobre cashback, no relacionados;
no se tocaron.)

## Contrato del payload (webhook Workflow A)

Evento `tickets.created`, que Odoo debería enviar por `POST` al webhook de
n8n cada vez que se crean folios nuevos para un cliente
(`raffle.ticket._create_for_order` / `_create_for_daily_block`):

```json
{
  "event": "tickets.created",
  "campaign": {
    "id": 12,
    "name": "52 Aniversario",
    "code": "52A"
  },
  "partner": {
    "id": 345,
    "name": "Juan Pérez",
    "phone": "+525512345678"
  },
  "tickets": {
    "count": 3,
    "folios": ["52A-R-000123", "52A-R-000124", "52A-R-000125"]
  },
  "portal_url": "https://<dominio-portal>/my/raffles"
}
```

Justificación de cada campo (todos trazables a modelos reales):

- `campaign.id/name/code`: `raffle.campaign.name` / `.code`.
- `partner.id/name/phone`: `res.partner`. **Ojo:** Odoo 19 consolidó
  `mobile` en `phone` (no hay campo `mobile` separado) — se espera formato
  E.164 (`+52...`). Si `phone` viene vacío o no matchea `+[1-9]\d{7,14}`,
  el workflow lo trata como inválido y **no** intenta enviar (ver manejo de
  error abajo), en vez de fallar silenciosamente.
- `tickets.count/folios`: boletos nuevos de este evento — `raffle.ticket.name`
  (folio, ej. `"52A-R-000123"`) para cada registro creado en el mismo lote.
- `portal_url`: apunta a `/my/raffles`, la ruta portal ya existente
  (`controllers/portal.py`, `RafflePortal.portal_my_raffles`).

No se incluyeron campos como `origin_type`, `rule_id` o `legacy_ref` en el
payload del webhook: son detalles internos de trazabilidad de folio que no
aportan nada al mensaje de WhatsApp del cliente — se evitó sobre-diseñar el
contrato.

## Workflow A — `raffle_whatsapp_notify.json`

1. **Webhook - Boletos Creados** (`POST /webhook/raffle-tickets-created`,
   `responseMode: responseNode`): recibe el payload de arriba.
2. **Validar y Formatear Mensaje** (Code): normaliza el teléfono, valida
   formato E.164, arma un preview de folios (máx. 5 + "y N más") y deja los
   campos listos para los parámetros posicionales de la plantilla.
3. **¿Teléfono válido?** (IF): rama según `has_valid_phone`.
   - **Falso** → **Responder Teléfono Faltante**: responde `200` con
     `{"status":"skipped","reason":"missing_or_invalid_phone", ...}` — no
     intenta enviar, no rompe el flujo.
   - **Verdadero** → **Enviar Plantilla WhatsApp** (HTTP Request a
     `https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages`,
     `type: "template"`, plantilla `raffle_new_tickets` con 4 parámetros
     posicionales: nombre, conteo, folios, nombre de campaña).
     - Éxito → **Responder OK** (`200`).
     - Error (`onError: continueErrorOutput`, segundo output del nodo) →
       **Responder Error Envío** (`502` con detalle) — tampoco falla
       silenciosamente.

Los mensajes usan **Message Template** (no texto libre), como exige la
Cloud API fuera de la ventana de 24h de conversación abierta por el cliente.
La plantilla `raffle_new_tickets` debe crearse y aprobarse en Meta Business
Manager antes de activar el workflow, con este cuerpo de ejemplo (variables
posicionales `{{1}}..{{4}}`):

```
Hola {{1}}, ya tienes {{2}} boleto(s) nuevo(s) en la rifa: {{3}}.
Campaña: {{4}}. Consulta tus boletos en el portal.
```

## Workflow B — `raffle_whatsapp_summary.json`

1. **Disparador Diario** (Schedule Trigger, cron `0 9 * * *` = 09:00 todos
   los días, timezone de la instancia n8n). **Ajustar el cron según
   necesidad real** (ej. solo en fechas cercanas al sorteo) — se dejó
   comentado a propósito para que nadie lo confunda con "cada minuto".
2. **Login Odoo (JSON-RPC)**: `POST {ODOO_URL}/jsonrpc`,
   `service: "common", method: "login"` con `ODOO_DB` / `ODOO_LOGIN` /
   `ODOO_API_KEY` (variables de entorno de la instancia n8n, no van en el
   JSON). Ver "Supuesto sobre el endpoint de lectura" abajo.
3. **Leer raffle.ticket.summary**: `execute_kw` (`search_read`) sobre
   `raffle.ticket.summary`, filtrando `campaign_id.state in ('active','closed')`,
   trayendo `partner_id, campaign_id, ticket_count, physical_count,
   online_count, legacy_refs`.
4. **Extraer IDs de Clientes y Aplanar Resumen** (Code): aplana los
   many2one (`[id, display_name]`) y junta los `partner_id` únicos.
5. **Leer Teléfonos de Clientes**: `execute_kw` (`search_read`) sobre
   `res.partner` con `id in [...]`, trae `id, name, phone`. Necesario porque
   `raffle.ticket.summary` (vista SQL) no expone teléfono.
6. **Combinar Resumen y Teléfono** (Code): une ambos resultados por
   `partner_id`, valida formato E.164 y arma un item por (cliente, campaña)
   con `to`, `partner_name`, `campaign_name`, `ticket_count`, `portal_url`.
7. **Loop Over Items - Lote de Envío** (SplitInBatches, `batchSize: 1`):
   procesa un cliente a la vez.
   - **¿Teléfono válido?** (IF) → si no, **Registrar Teléfono Faltante**
     (Set, marca `status: skipped_no_phone`) y vuelve al loop.
   - Si sí → **Enviar Resumen WhatsApp** (mismo patrón de plantilla
     aprobada, `raffle_ticket_summary`, 3 parámetros: nombre, total de
     boletos, nombre de campaña).
     - Éxito → **Espera entre envíos** (Wait, 2s) → vuelve al loop.
     - Error → **Registrar Error de Envío** (Set, marca `status: send_error`,
       no pierde el item) → vuelve al loop.
   - Salida `done` del loop → **Fin - Resumen de Cierre Enviado** (NoOp;
     el detalle de envíos/omitidos/errores de la corrida queda visible en
     la pestaña **Executions** de n8n).

El `batchSize: 1` + `Wait` de 2s entre envíos es el throttling básico exigido
por la tarea (~30 mensajes/min) para no pegarle de golpe a los rate limits de
WhatsApp Business Cloud API. **Ajustar el tiempo de espera según el tier de
mensajería real de la cuenta de Meta** antes de usarlo con un padrón grande
de clientes.

### Supuesto sobre el endpoint de lectura (Workflow B)

Se asumió el endpoint **estándar** de Odoo `/jsonrpc` (`service: "common"` /
`service: "object"`, patrón `login` + `execute_kw`) en vez de un endpoint
REST custom, porque:

- Existe en cualquier instalación Odoo 19 sin tocar nada del módulo
  `mds_raffle_campaign` (la tarea pide explícitamente no modificar ese
  código).
- Es el mecanismo público y documentado de Odoo para integraciones externas
  (equivalente JSON-RPC del XML-RPC clásico).

Si en el futuro se prefiere un endpoint REST custom (similar en espíritu al
`/my/rifa` que ya existe en `controllers/portal.py`, pero con auth de
API key en vez de sesión de portal), habría que agregar ese controller al
módulo y reemplazar los dos nodos HTTP Request de login/lectura por uno solo.

## Credenciales y variables de entorno a configurar en n8n ANTES de importar

**Credencial de n8n** (Settings → Credentials → New):

- Tipo: **HTTP Header Auth**.
- Nombre exacto: `WhatsApp Cloud API - Rifas` (los dos workflows la
  referencian por este nombre; si se usa otro nombre hay que reasignarla
  manualmente en los nodos "Enviar Plantilla WhatsApp" / "Enviar Resumen
  WhatsApp" después de importar — la referencia por `id` en el JSON es un
  placeholder que no existirá en la instancia destino).
- Header: `Authorization`, valor: `Bearer <token de Meta Cloud API>`.

**Variables de entorno de la instancia n8n** (además de las ya listadas en
el `README.md` general de esta carpeta — `ODOO_URL`, `ODOO_DB`):

| Variable | Uso | Notas |
|---|---|---|
| `ODOO_URL` | Base para `/jsonrpc` (Workflow B) | Ya existe para otros workflows de esta carpeta. |
| `ODOO_DB` | Nombre de la base de datos | Ya existe para otros workflows de esta carpeta. |
| `ODOO_LOGIN` | Usuario de servicio para JSON-RPC (Workflow B) | Nuevo — usar un usuario técnico dedicado, no una cuenta personal. |
| `ODOO_API_KEY` | API Key de ese usuario (Odoo → Preferencias → Cuentas y Seguridad → API Keys) | Nuevo. Nunca va en el JSON. |
| `WHATSAPP_PHONE_NUMBER_ID` | Segmento de la URL de Graph API (Workflows A y B) | Coincide con `whatsapp_phone_number_id` de `res.config.settings` en Odoo — mantener sincronizado si cambia. |
| `PORTAL_BASE_URL` | Dominio del portal para armar `portal_url` (Workflow B) | Ej. `https://portal.medicinedepot.mx`. |

El token de WhatsApp (`whatsapp_api_token` en Odoo) **no** se reutiliza como
variable de entorno de n8n — en n8n vive únicamente dentro de la credencial
`WhatsApp Cloud API - Rifas` de arriba.

## Cómo importar

Mismo procedimiento que el resto de workflows de esta carpeta (ver
`README.md` general): en la UI de n8n, **Workflows → Add Workflow → Import
from File**, seleccionar `raffle_whatsapp_notify.json` o
`raffle_whatsapp_summary.json`. Después de importar:

1. Reasignar la credencial `WhatsApp Cloud API - Rifas` en los dos nodos
   HTTP Request que la usan (el `id` de credencial del JSON es un
   placeholder, no existirá en la instancia destino).
2. Confirmar que las variables de entorno de la tabla de arriba estén
   configuradas en el proceso de n8n (no solo en el workflow).
3. Activar (`Active: ON`) cada workflow solo después de probar una ejecución
   manual/de prueba.

## Precaución: `workflow_history` en la base de n8n

Si en algún momento alguien decide cargar estos JSON directamente por SQL
contra la base de datos de n8n (`workflow_entity.nodes`) en vez de por la UI
o la API de n8n, **eso no es suficiente** para que el workflow tome el
cambio en runtime: n8n lee de `workflow_history`, no solo de
`workflow_entity`. Ya pasó en este proyecto (ver notas de sesiones previas
sobre el fix del bucle `04`) que un `UPDATE` directo a `workflow_entity.nodes`
quedó "aplicado" en la tabla pero el runtime seguía ejecutando la versión
vieja. La forma soportada de importar/actualizar estos workflows es **UI
(Import from File) o API de n8n**, no escritura directa en la base.

## Supuestos sobre el formato de export de n8n

No tengo acceso a un n8n real en este entorno para exportar un workflow de
referencia y comparar. La forma usada aquí (`name`, `nodes[]` con `id`,
`name`, `type`, `typeVersion`, `position`, `parameters`, y `connections`
como mapa `{"<nombre del nodo origen>": {"main": [[...]]}}`) sigue el patrón
documentado públicamente por n8n y es consistente con el resto de archivos
`.json` ya presentes en esta carpeta (ej. `15_alertas_anomalias_cashback.json`).
Detalles donde fui deliberadamente conservador:

- **`typeVersion`** de cada nodo (`webhook: 2`, `code: 2`, `if: 2`,
  `httpRequest: 4.2`, `respondToWebhook: 1.1`, `scheduleTrigger: 1.2`,
  `splitInBatches: 3`, `wait: 1.1`, `set: 3.4`, `noOp: 1`): son las
  versiones más recientes que conozco de cada nodo nativo, pero n8n
  actualiza estos nodos con cierta frecuencia. Si al importar la UI muestra
  una advertencia de "node version mismatch", basta con abrir el nodo y
  guardarlo — n8n migra el parámetro a la versión instalada.
- **`onError: "continueErrorOutput"`** en los nodos HTTP Request: es el
  mecanismo real de n8n para bifurcar en un segundo output de error sin que
  el nodo lance excepción y detenga el workflow. Si la versión de n8n
  instalada no lo soporta, la alternativa manual es activar
  "Continue On Fail" en el nodo y usar un nodo IF posterior sobre
  `$json.error`.
- **`jsonBody` como expresión de objeto** (`={{ {...} }}` en vez de texto
  JSON con placeholders `{{ }}` incrustados): es el patrón recomendado del
  HTTP Request node v4+ para evitar problemas de escapado de comillas; se
  usó consistentemente en ambos workflows.
- **Credencial referenciada por `id` + `name`**: el `id` es un placeholder
  (`whatsapp-cloud-api-rifas`) — n8n no lo va a encontrar en una instancia
  nueva y pedirá reasignar la credencial manualmente tras importar (ver
  sección de importación arriba).
- No incluí `versionId` ni `id` de workflow a nivel raíz (n8n los genera al
  guardar); si al importar la UI los pide, no afecta la estructura de nodos.
- **Orden de outputs de `splitInBatches`** (Workflow B, nodo "Loop Over
  Items - Lote de Envío"): asumí `output 0 = "done"`, `output 1 = "loop"`
  (el orden documentado históricamente por n8n para este nodo). Si al
  importar se ve que las ramas quedaron invertidas (el resumen final se
  dispara antes de procesar clientes, o nunca se llega al NoOp), basta con
  arrastrar las conexiones de esos dos outputs al revés en el canvas — es
  un ajuste visual, no estructural.
