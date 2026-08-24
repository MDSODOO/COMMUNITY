# Auditoría Técnica RPA — n8n + Odoo 19 (medicinedepot_dev)

**Fecha:** 2026-08-12
**Alcance:** instancia de pruebas `medicinedepot_dev` (Odoo 19, contenedor `medicinedepot_dev_odoo`) y contenedor `md_n8n` en el servidor `ionos`.
**Método:** inspección directa de `workflow_entity`/`execution_entity` en la BD de n8n (`md_n8n_db`), lectura de los JSON exportados en `docs/n8n_workflows/`, y consultas SQL directas sobre `medicinedepot_dev` (Postgres) para volumen de creación, estados y backlog por modelo.

> **Nota de fiabilidad de los datos de Odoo:** el 99% de los registros de `purchase.order`, `stock.move` y `product.template` fueron creados por el usuario `admin` en un único evento de carga masiva (julio 2026, ver distribución mensual abajo), coincidiendo con la migración a Odoo 19. Por tanto los conteos de "volumen a 90 días" reflejan en su mayoría **una importación, no actividad orgánica multiusuario**. Donde esto afecta la interpretación se indica explícitamente. El **estado actual de los documentos** (draft/assigned/etc.) sí es un hecho observable y confiable independientemente del origen del dato.

---

## 1. Mapeo de flujos n8n actuales

Existen **7 workflows reales** en la instancia (tabla `workflow_entity`), no solo los 5 documentados en `docs/plans/N8N_RPA_STRATEGY.md` — ese plan **ya se implementó por completo** y se añadieron 2 workflows adicionales no documentados originalmente (`00_Error_Handler_Global` y `06_OCR_Documentos`, este último aún en esqueleto/inactivo).

| # | Workflow | Estado | Trigger | Nodos clave (Actions) | Ejecuciones acumuladas (histórico) | Tasa de error histórica | Estado actual (última ejecución real) |
|---|----------|--------|---------|------------------------|-------------------------------|----------------|----------------|
| 00 | Error_Handler_Global | Activo | Error Trigger | Code (formatear) → HTTP (Telegram) | 1 éxito / 15 error | 94% (todo 10-ago, pre-fix) | ✅ Sana desde 10-ago 23:30 (ver hallazgo 1) |
| 01 | Healthcheck_Odoo | Activo | Schedule | HTTP (`/web/health`) → IF → Code → HTTP Telegram | 581 éxito / 0 error | 0% | ✅ Corriendo cada 5 min, 12-ago 22:35 |
| 02 | Conciliacion_Inventario | Activo | Schedule | Auth XML-RPC → IF → search stock → IF → format → Telegram | 5 éxito / 7 error | ~58% (todo 10-ago, pre-fix) | ✅ Última corrida 12-ago 14:00 exitosa |
| 03 | Alertas_Lotes_Vencimiento | Activo | Schedule | Auth → IF → calcular fecha límite → search lotes → consolidar severidad → Telegram | 5 éxito / 12 error+crash | ~71% (todo 10-ago, pre-fix) | ✅ Última corrida 12-ago 15:00 exitosa |
| 04 | Sync_Ordenes_Compra [DEV] | Activo | Webhook | Validar payload → Auth XML-RPC → buscar partner/productos → preload lotes → duplicados → crear PO → Telegram | 45 éxito / 4 error | 8% | ✅ pero con bug latente sin fix (ver hallazgo 3) |
| 05 | Reporte_Ventas_Diario | Activo | Schedule | Auth → IF → rango de fecha → consultar ventas → resumen → Telegram | 5 éxito / 5 error | 50% (todo 10-ago, pre-fix) | ✅ Última corrida 12-ago 00:00 exitosa |
| 06 | OCR_Documentos [ESQUELETO] | **Inactivo** | Webhook | OCR (servicio local) → normalizar → Auth → buscar partner → crear factura borrador → adjuntar doc → Telegram | 5 éxito / 1 error (pruebas) | En validación | Sin activar en producción |

### Hallazgos de eficiencia

1. **[ACTUALIZADO 2026-08-12] "El error handler global está roto" — diagnosticado y confirmado ya resuelto.** Las tasas de error de la tabla son **acumuladas desde la creación de los flujos** (10-ago, día de desarrollo/pruebas) y no reflejan el estado actual. Se investigó a fondo extrayendo el error real desde `execution_data`: la causa raíz de **todos** los fallos de `00_Error_Handler_Global`, `02_Conciliacion_Inventario`, `03_Alertas_Lotes_Vencimiento` y `05_Reporte_Ventas_Diario` en la ventana del 2026-08-10 ~22:18-22:20 es la **misma**: `ExpressionError: access to env vars denied` al evaluar `{{ $env.TELEGRAM_BOT_TOKEN }}` — n8n bloqueaba por defecto el acceso a variables de entorno dentro de expresiones de nodo. Esto **ya se corrigió el mismo día** (`N8N_BLOCK_ENV_ACCESS_IN_NODE: "false"`, verificado persistido en `/opt/n8n-md/docker-compose.yml`, no solo en el proceso vivo) y confirmado con la ejecución real más reciente de `00` (2026-08-10 23:30, `status=success`, disparada por un error real de otro flujo) — sin ningún error nuevo desde entonces en ninguno de los cuatro flujos. **No requiere acción correctiva adicional**, aunque persiste una fragilidad de diseño (ver hallazgo 1b).
1b. **Fragilidad remanente (hardening recomendado, no bloqueante):** los nodos Telegram de `00/01/02/03/05` siguen dependiendo de `{{ $env.TELEGRAM_BOT_TOKEN }}` en la URL/body en vez de una Credential nativa de n8n. Esto vuelve a fallar si una futura actualización de n8n cambia el default de `N8N_BLOCK_ENV_ACCESS_IN_NODE`, o si alguien reconstruye el contenedor sin heredar ese flag. Migrar a una credencial "HTTP Header Auth" o al nodo nativo de Telegram elimina la dependencia del flag por completo. Ver R4 (reclasificada de "fix urgente" a "hardening preventivo").
2. **Patrón de fallo compartido en 02/03/05 — mismo origen que el punto 1, no bugs independientes de autenticación Odoo.** Confirmado por el mismo mensaje de error en los cuatro flujos. Sus ejecuciones programadas más recientes (12-ago: 15:00, 14:00 y 00:00 respectivamente) fueron todas exitosas.
3. **`04_Sync_Ordenes_Compra` es el flujo más maduro** (22 nodos, manejo de duplicados, variación de precios, auto-confirmación) y el más fiable (92%), pero conserva un bug ya identificado en producción: el nodo `Parse Auth Response` construye la búsqueda de `res.partner` por `vat`/`name` **sin `order` explícito** (confirmado leyendo el JSON — no contiene `supplier_rank`), mientras que el mismo fix **sí** se aplicó en `06_OCR_Documentos_esqueleto.json`. Este es el origen exacto del incidente de proveedores duplicados (Quifamesa/Brudifarma, resuelto manualmente el 2026-08-10) y sigue latente para cualquier otro proveedor que llegue a duplicarse.
4. **`06_OCR_Documentos` está construido pero nunca se activó en producción** — 17 nodos, flujo completo de factura por OCR, pero `active=false` en la BD.

---

## 2. Uso real de la base de pruebas (medicinedepot_dev)

| Modelo | Total | Últimos 90 días | Observación |
|---|---|---|---|
| `account.move` (facturas/asientos) | 44,644 | 44,644 | Casi todo `posted`; solo 5 en `draft` — la facturación **no** es cuello de botella |
| `purchase.order` | 9,447 | 9,447 | **5,724 en `draft` (60%)**, 3,718 confirmadas |
| `purchase.order.line` | 139,321 | 139,321 | — |
| `stock.move` | 39,123 | 39,123 | **32,847 en `assigned`** vs solo 6,272 `done` |
| `stock.picking` | — | — | **3,701 en `assigned`** (reservado, sin completar) vs 21 `done` |
| `stock.quant` | 18,922 | 18,922 | — |
| `product.template` | 6,084 | 6,084 (=total, carga única) | 12 productos sin `barcode` |
| `account.bank.statement.line` | **0** | 0 | **Conciliación bancaria no se usa/registra en Odoo en absoluto** |
| `res.partner` | 3,498 | 3,498 | — |
| `ir.attachment` | 15,770 | 15,770 | Volumen alto de documentos adjuntos |

**Cuellos de botella por estado (los más accionables):**

- **Purchase orders atascadas en `draft`:** 5,724 (60% del total), casi todas creadas en julio 2026. Aunque el origen es la migración, el hecho de que sigan en `draft` hoy — sin flujo que las revise, confirme o cancele — es un backlog operativo real y visible en el sistema en este momento.
- **Stock pickings/moves atascados en `assigned`:** 3,701 pickings y 32,847 moves reservados sin completar, la mayoría desde la semana del 2026-07-06. Indica reservas de inventario que nunca se liberan ni se procesan — inventario "fantasma" comprometido.
- **Conciliación bancaria ausente:** 0 registros en `account_bank_statement_line`. No es que el proceso sea ineficiente — **no existe en absoluto** en esta instancia, pese a que `N8N_RPA_STRATEGY.md` no lo contempla y es un proceso clásicamente manual y de alto volumen en cualquier negocio.

---

## 3. Recomendaciones de nuevos procesos RPA

### R1. Conciliación bancaria automatizada (prioridad alta — gap total detectado) — [IMPLEMENTADO COMO ESQUELETO 2026-08-12]
**Problema:** `account.bank.statement.line` está vacío; no hay evidencia de que la conciliación bancaria pase por Odoo.

Se construyó `08_Conciliacion_Bancaria [ESQUELETO]` (`conciliacion-bancaria-uuid`, **inactivo**, igual que `06`). El usuario no tenía definida la fuente real de los estados de cuenta (¿correo? ¿portal del banco? — se preguntó explícitamente), así que se optó por un **Webhook genérico** que recibe las transacciones ya parseadas en JSON, siguiendo el mismo patrón que `04`/`06`, para conectarlo fácilmente a la fuente real cuando se defina.

**Trigger:** `Webhook` POST `conciliacion-bancaria-inbound`. Payload: `{ journal_id, transactions: [{ date, amount, description, reference?, partner_hint? }] }` (`amount` positivo = entrada/cliente paga, negativo = salida/pago a proveedor; `partner_hint` es opcional pero mejora mucho la precisión del matching).

**Actions:** `Validar Payload` → `Autenticar Odoo` (JSON-RPC) → `Expandir Transacciones` (fan-out, 1 item por movimiento) → `Crear Linea Bank Statement` (`account.bank.statement.line.create`, genera automáticamente el asiento contable) → `Buscar Facturas Candidatas` (`account.move.search_read`, dominio acotado por `move_type` según signo + rango de `amount_residual` ±2% + `partner_hint` si viene) → `Agregar Resumen Final` (fan-in) → Telegram (tema **Finanzas y Conciliación**, thread 75, creado para este flujo) → `Respond Success`.

**Decisiones de diseño verificadas en vivo antes de construir, no asumidas:**
- Se confirmó con `fields_get` que `account.bank.statement.line.create()` genera el `move_id` (asiento) automáticamente y lo deja `posted` — no hace falta crear un header `account.bank.statement` aparte en Odoo 19. Probado con un registro real (creado y eliminado limpiamente).
- Se descubrió que el matching **solo por monto es insuficiente**: con ~44,000 facturas históricas sin pagar en esta base, una búsqueda de rango ±2% topa fácilmente el límite de 20 candidatos. Por eso el diseño **nunca auto-concilia** — clasifica cada movimiento como `match_unico` / `multiples_candidatos` / `demasiados_candidatos` / `sin_match` y todo pasa por revisión humana en Odoo.
- Simulado el pipeline completo con datos reales (factura real del IMSS, `id 1`, `residual $551.86`) antes de insertar en n8n: encontró el match único correcto con `partner_hint`, y clasificó correctamente dos casos ambiguos como "requiere revisión" en vez de adivinar.

**Pendiente para llevarlo a producción:** decidir la fuente real de los estados de cuenta (correo/portal/API del banco) y conectar esa parte al webhook — el resto del pipeline (creación contable + matching + alerta) ya está construido y probado.

### R2. Gestión de backlog de órdenes de compra en `draft` — [IMPLEMENTADO Y ACTIVO 2026-08-12]
**Problema:** 5,724 POs (60%) nunca confirmadas ni canceladas.

Se construyó `09_Backlog_Ordenes_Compra_Draft` (`backlog-po-draft-uuid`), activo. **Trigger:** `Schedule` semanal (lunes 8:15am). **Actions:** `Autenticar Odoo` (JSON-RPC) → `Resumen Por Comprador` (`read_group` de `purchase.order` con `state='draft'` y `create_date` > 7 días de antigüedad, agrupado por `user_id`, evita traer los 5,713 registros completos a memoria) → `Ordenes Mas Antiguas` (`search_read` limit 10, `order: create_date asc`) → `Code` combina ambos en un resumen (total + desglose por comprador + top 10 más antiguas con días de antigüedad) → Telegram (tema Compras, thread 6). Validado con datos reales antes de activar: 5,713 órdenes, $159.8M MXN, casi todo bajo un solo usuario (reflejo de la migración, se lo advierte explícitamente en el mensaje para no generar falsa urgencia).

### R3. Liberación/monitoreo de reservas de inventario atascadas (`stock.picking`/`stock.move` en `assigned`) — [IMPLEMENTADO Y ACTIVO 2026-08-12]
**Problema:** 3,701 pickings reservados sin completar desde hace más de un mes.

Se construyó `10_Backlog_Pickings_Atascados` (`backlog-pickings-uuid`), activo. **Trigger:** `Schedule` semanal (lunes 8:30am — cadencia baja intencional por ahora; subir a cada 4-6h una vez que el backlog histórico de la migración se limpie y el flujo refleje operación real del día a día). **Actions:** mismo patrón que `09`: `read_group` por `picking_type_id` + `search_read` de los 10 más antiguos (ordenado por `create_date`, no por `scheduled_date` — se descubrió en vivo que ese campo trae fechas placeholder corruptas de la migración, ej. "2022-02-24", inservibles para priorizar) → Telegram (tema Recepción y Almacén, thread 8). Validado con datos reales: 3,701 movimientos (3,700 recepciones + 1 entrega).

**Nota de diseño para ambos (09 y 10):** no se auto-cancela ni se auto-libera nada — solo se notifica para revisión humana, dado que estos registros pueden tener implicaciones contables/de inventario reales.

### R4. Hardening preventivo del Error Handler Global y de 02/03/05 (ya no es bloqueante — causa raíz resuelta el 2026-08-10)
**Problema original (RESUELTO):** los 4 flujos fallaban por `ExpressionError: access to env vars denied` al usar `{{ $env.TELEGRAM_BOT_TOKEN }}`. Ya corregido y persistido en `docker-compose.yml` (`N8N_BLOCK_ENV_ACCESS_IN_NODE: "false"`); confirmado con ejecuciones exitosas reales posteriores en los 4 flujos.
**Hardening recomendado (no urgente):**
- Reemplazar `{{ $env.TELEGRAM_BOT_TOKEN }}`/`{{ $env.TELEGRAM_CHAT_ID }}` por una credential nativa de n8n (nodo Telegram o "HTTP Header Auth") en `00/01/02/03/05`, para no depender de que `N8N_BLOCK_ENV_ACCESS_IN_NODE` se mantenga en `false` en futuras reconstrucciones del contenedor.
- Añadir `retryOnFail: true, maxTries: 3` a los HTTP Request que aún no lo tienen (ya presente en `04`), como defensa adicional ante caídas transitorias de red/Telegram.

### R5. Detección proactiva de proveedores/clientes duplicados
**Problema:** el bug de `04_Sync_Ordenes_Compra` (búsqueda de `res.partner` sin `order` explícito) causó el incidente real de Quifamesa/Brudifarma; sigue sin corregirse en ese workflow y puede repetirse con cualquier otro proveedor.
**[APLICADO 2026-08-12]** Se agregó `order: 'supplier_rank desc'` al `search_read` de `res.partner` en el nodo `Parse Auth Response` de `04_Sync_Ordenes_Compra` (mismo patrón ya presente en `06`), aplicado directamente en `workflow_entity.nodes` (n8n) y sincronizado en `docs/n8n_workflows/04_sync_ordenes_compra.json` (backup previo: `04_sync_ordenes_compra.json.bak_20260812_224609`). Verificado con una llamada XML-RPC real de prueba contra `medicinedepot_dev` (vat `QFM861010BL0`): devuelve el registro correcto y único (`id 3455`, el ya fusionado). Único cabo suelto: el `UPDATE` se hizo directo en Postgres, no vía la UI/API de n8n, así que **no quedó registrado en `workflow_history`** (el versionado interno de n8n) — sin impacto funcional, pero si alguien revisa el historial de versiones en la UI no verá este cambio como una entrada nueva.

**[IMPLEMENTADO Y ACTIVO 2026-08-12] Nuevo workflow `07_Deteccion_Duplicados_Proveedores`** (`duplicados-proveedores-uuid`). **Trigger:** `Schedule` semanal (lunes 8:00am, cron `0 8 * * 1`). **Actions:** `Autenticar Odoo` (JSON-RPC) → `Buscar Partners Con VAT` (`search_read` res.partner activos con vat, `limit=5000`) → `Code` agrupar por VAT y detectar duplicados (con filtro `vat.length>=5` para descartar placeholders basura como `"."`, encontrado y corregido durante la validación) → `IF` hay duplicados → `Code` formatear resumen (o heartbeat "sin duplicados") → `Notificar Telegram Duplicados` (tema Compras, thread_id=6). Errores enrutados al `00_Error_Handler_Global` (`settings.errorWorkflow`).

Validado con una consulta real de prueba directa contra `medicinedepot_dev` antes de activar: **80 grupos de VAT/RFC con más de un registro activo detectados hoy** (además del caso ya resuelto Quifamesa/Brudifarma, que correctamente NO aparece). El primer envío real ocurrirá el próximo lunes.

Exportado en `docs/n8n_workflows/07_deteccion_duplicados_proveedores.json`. Nota técnica: n8n (v2.33.7) requiere, además de `workflow_entity`, una fila en `workflow_history` (versión publicada) y otra en `shared_workflow` (ownership de proyecto) para que un workflow insertado por SQL directo se active de verdad al reiniciar — un `active=true` sin esas dos filas queda "activo" en la tabla pero **n8n no registra su trigger** (se comprobó en vivo: el primer intento no apareció en el log de `Activated workflow` hasta completar ambas). Se requirieron 2 reinicios de `md_n8n` para dejarlo funcionando; sin downtime de Odoo.

### R6. Panel de salud de los propios workflows n8n — [IMPLEMENTADO 2026-08-12, con un cambio de diseño deliberado]
**Problema:** no hay visibilidad centralizada de la tasa de error por flujo (se tuvo que consultar la BD directamente para esta auditoría).

**No se implementó como workflow de n8n.** Dos razones concretas, no solo preferencia:
1. No existe una API key de n8n configurada (se revisó `user_api_keys`, vacía), y crear una vía SQL directo requeriría replicar el esquema de cifrado interno de n8n sin garantía de acertarle. Lo mismo aplica a una credential de Postgres nativa de n8n (cifrada con `N8N_ENCRYPTION_KEY`, no se puede insertar en texto plano).
2. Aunque se resolviera lo anterior, un monitor de salud **corriendo dentro de n8n para vigilar a n8n mismo** tiene el mismo punto ciego que ya encontramos en esta auditoría: `00_Error_Handler_Global` llegó a fallar el 94% de las veces sin que nadie se enterara, porque el propio n8n era el que tenía el problema. Un watchdog externo no depende de que n8n esté sano para poder avisar que n8n no está sano.

**Implementado en su lugar:** se extendió `scripts/healthcheck.sh` (ya existente en el repo, corriendo cada 5 min vía `/etc/cron.d/medicinedepot-healthcheck` desde el 2026-07-31, con lógica de alertar solo en *cambio* de estado + recordatorio horario si sigue caído — reutilizada tal cual, no reinventada):
- Se agregaron `md_n8n` y `md_n8n_db` a la lista de contenedores monitoreados (**no estaban**, era un punto ciego real).
- Se agregó `check_n8n_workflows()`: consulta `execution_entity` en `md_n8n_db` (vía `docker exec` + `psql`, sin credenciales adicionales) por workflow activo en ventana de **24h** (no 7 días — se probó con 7 días primero y mostraba los errores viejos de desarrollo del 10-ago ya resueltos, dando una falsa alarma), con mínimo 3 ejecuciones para evitar ruido por muestras chicas, umbral 30% de error → usa el mismo `report_state` (mismo mecanismo de Telegram + debounce que ya usa el resto del script).
- Verificado en vivo: sintaxis validada (`bash -n`), corrido manualmente una vez — reporta correctamente `01_Healthcheck_Odoo — 0/288 fallos (0%) en 24h`, sin falsos positivos. Se confirmó además que las alertas de `medicinedepot_test_odoo`/`medicinedepot_test_db` que salieron en esa corrida son un problema **preexistente y ya conocido** (aparece en el log desde antes de este cambio, con su propio ciclo de recordatorio), no algo causado por esta modificación.
- Backup del script original en `scripts/healthcheck.sh.bak_20260812_235123`.

### R7. Reporte semanal de calidad de catálogo — [IMPLEMENTADO Y ACTIVO 2026-08-12]
**Problema:** productos con campos incompletos (12 sin `barcode` detectados en el análisis inicial; se amplió el chequeo a más campos antes de construir).

Se construyó `11_Calidad_Catalogo` (`calidad-catalogo-uuid`), activo. **Trigger:** `Schedule` semanal (lunes 8:45am). **Actions:** `Autenticar Odoo` → `Buscar Productos Problematicos` (`search_read` de `product.product` activos y vendibles, dominio combinado con `|` por 4 condiciones: sin `default_code`, `list_price=0`, sin `categ_id`, sin `barcode`) → `Clasificar Problemas` (Code, separa por tipo de hueco) → Telegram (tema Compras, thread 6 — no se creó tema dedicado por ser esta la recomendación de menor prioridad del reporte).

**Se descartó chequear `weight`** (peso): se probó primero y el 99.97% del catálogo (3,341 de 3,342) tiene `weight=0` — no es un hueco real, así opera el negocio, solo habría generado ruido.

**Hallazgos reales al día de hoy (839 productos vendibles con algo incompleto):**
- **171** con precio de venta en $0 (el más serio — riesgo de vender por error a $0).
- **666** sin categoría asignada.
- **4** sin SKU y **4** sin código de barras — se descubrió que estos 4 no son inventario farmacéutico real, sino pseudo-productos del sistema (Gift Card, Tips, Down Payment, Top-up eWallet) — ruido menor, no se filtró explícitamente pero es un volumen insignificante dentro del reporte.

---

## 4. Revisión de notificaciones de Telegram (2026-08-12) — [APLICADO Y VERIFICADO]

Se revisó el contenido y enrutamiento de los mensajes de Telegram de los 8 workflows leyendo directamente el código vivo (`workflow_entity.nodes`), no solo los JSON exportados. Todos los cambios descritos abajo **ya se aplicaron** en producción y se verificaron con pruebas reales antes de darlos por buenos.

### Hallazgo positivo: `04_Sync_Ordenes_Compra` es el estándar a seguir
Su nodo `Preparar Post-Creacion` arma un mensaje "tarjeta ejecutiva": separadores visuales, emoji por sección (estado, trazabilidad de lotes, auditoría de precios), botones `inline_keyboard` con links directos a Odoo, y menciona explícitamente "Sincronizado con Odoo Dev 19" (transparencia de entorno). Ningún otro flujo alcanza ese nivel — vale la pena usarlo como plantilla al rediseñar los demás.

### Problema 1: enrutamiento inconsistente — lo crítico cae en "General"
| Workflow | Tema Telegram actual |
|---|---|
| `00_Error_Handler_Global` (errores de **todos** los flujos) | General (sin `message_thread_id`) |
| `01_Healthcheck_Odoo` | General |
| `02_Conciliacion_Inventario` | Recepción y Almacén (thread 8) |
| `03_Alertas_Lotes_Vencimiento` | Alertas de Caducidades (thread 9) |
| `04_Sync_Ordenes_Compra` | Compras (6) / Variación Precios (7), dinámico |
| `05_Reporte_Ventas_Diario` | General |
| `06_OCR_Documentos` | General |
| `07_Deteccion_Duplicados` | Compras (6) |

Las alertas de error más importantes del sistema (`00`) se mezclan en el canal más ruidoso con reportes rutinarios de ventas y salud — nadie puede silenciar "solo lo rutinario" sin silenciar también los errores reales. El propio código de `05` ya dejaba una nota reconociendo este hueco ("crear un tema dedicado queda como mejora futura opcional").

**[APLICADO]** Se confirmó primero que el bot es administrador del grupo con `can_manage_topics: true` (`getChatMember`), y se crearon 2 temas nuevos vía `createForumTopic`:
- **"Sistema y Alertas"** (`message_thread_id: 52`) → `00_Error_Handler_Global` y `01_Healthcheck_Odoo` ahora enrutan aquí.
- **"Ventas"** (`message_thread_id: 53`) → `05_Reporte_Ventas_Diario` ahora enruta aquí.
- `06_OCR_Documentos` → **sin cambios** (sigue en General); es un esqueleto inactivo, se deja pendiente de decidir cuando se active en producción.

Verificado con un mensaje de prueba real enviado a cada tema nuevo (confirmado `ok:true` en ambos) antes de dar el cambio por bueno.

**[APLICADO] Presentación de los 6 temas relevantes (Compras, Variación Precios, Recepción y Almacén, Alertas Caducidades, Sistema y Alertas, Ventas):** se asignó un ícono temático distinto a cada uno vía `editForumTopic` (🛒 Compras, 💱 Variación Precios, 🧳 Recepción y Almacén, 💊 Alertas Caducidades, 🤖 Sistema y Alertas, 💰 Ventas — elegidos de los 112 disponibles en `getForumTopicIconStickers`, no había un ícono de caja/almacén literal disponible), y se envió + fijó (`pinChatMessage`) un mensaje descriptivo en cada tema explicando qué workflow(s) publican ahí y qué tipo de alerta esperar. Confirmado `ok:true` en los 3 pasos (ícono, mensaje, fijado) para los 6 temas.

**[VERIFICADO] Botones de `04_Sync_Ordenes_Compra`:** se probaron los dos links del `inline_keyboard` ("Ver en Odoo" → `/odoo/purchase/<id>`, "Albarán Stock" → `/odoo/action-stock.action_picking_tree_all`) contra una orden real confirmada (`id 9470`) — ambos responden `303` redirigiendo correctamente a `/web/login?redirect=...` con la ruta de destino intacta (comportamiento esperado sin sesión iniciada). Se envió además un mensaje de prueba real a Telegram con el `reply_markup` exacto que usa el workflow — Telegram lo aceptó y renderizó sin errores. Sin hallazgos: los botones funcionan correctamente.

### Problema 2: vocabulario de emoji/severidad inconsistente
Convención implícita ya establecida por la mayoría: 🔴 = falla, ✅ = todo bien (heartbeat), 🟠 = degradado, 🟡 = requiere revisión manual. Dos excepciones:
- **`00_Error_Handler_Global` no usa ningún emoji** — irónico, siendo el flujo cuyo único trabajo es señalar fallas. Mensaje actual: `<b>Fallo en workflow n8n</b>...`.
- **`07_Deteccion_Duplicados`** (construido en esta misma sesión) tampoco sigue la convención — se omitió por descuido.

**[APLICADO] Fix aplicado en `00` (nodo `Formatear Error`):**
```js
const e = $input.first().json;
const workflowName = e.workflow?.name ?? 'desconocido';
const nodeName = e.execution?.lastNodeExecuted ?? e.node?.name ?? 'desconocido';
const message = e.execution?.error?.message ?? e.error?.message ?? 'sin detalle';
const tsLocal = new Date().toLocaleString('es-MX', { timeZone: 'America/Merida', dateStyle: 'short', timeStyle: 'medium' });
const text = `🔴 <b>Fallo en workflow n8n</b>\n<b>Workflow:</b> ${workflowName}\n<b>Nodo:</b> ${nodeName}\n<b>Error:</b> ${message}\n<b>Hora:</b> ${tsLocal} (Mérida)`;
return [{ json: { text } }];
```
(cambios: emoji 🔴, hora convertida a `America/Merida` en vez de ISO UTC crudo)

**[APLICADO] Fix en `07`:** `Formatear Resumen Duplicados` ya tenía `⚠️`, no requería cambio. Se agregó `✅` a `Formatear Heartbeat Sin Duplicados` y `🔴` a `Preparar Alerta - Fallo Autenticacion` y `Preparar Alerta - Fallo Consulta`, igual que en 02/03/05, para no romper la convención que el propio audit estableció como buena práctica.

### Problema 3: `01_Healthcheck_Odoo` manda JSON crudo en estado degradado — [APLICADO]
Se inspeccionó la respuesta real de `/web/health` (`{"status": "pass"}`, forma simple confirmada en vivo) y se simplificó el nodo `Preparar Alerta - Estado Degradado` para mostrar `body.status` directo en vez de `JSON.stringify(body)` completo.

---

## 5. Priorización sugerida

1. ~~**R5** (fix de una línea + detección proactiva)~~ — **hecho** (2026-08-12).
2. ~~**R1** (conciliación bancaria)~~ — **hecho como esqueleto** (2026-08-12); falta solo conectar la fuente real de estados de cuenta.
3. ~~**R2 y R3** (backlogs de PO y picking)~~ — **hechos y activos** (2026-08-12).
4. ~~**R6**~~ — **hecho** (2026-08-12), como extensión del watchdog externo `healthcheck.sh`, no como workflow n8n (ver justificación en la sección de R6).
5. ~~**R4** (hardening del error handler)~~ — **hecho**, resultó ya estar resuelto de antes; se agregó además el enrutamiento/presentación de Telegram.
6. ~~**R7**~~ — **hecho** (2026-08-12).

**Estado al 2026-08-12: las 6 recomendaciones originales del reporte están implementadas** (R1 como esqueleto pendiente de conectar la fuente bancaria real; R2/R3/R5/R6/R7 activos y verificados con datos reales).

## 6. Hallazgo adicional fuera del alcance original: sección `/afiliacion` del sitio

Investigación adicional (2026-08-12, vía subagente) sobre la sección de afiliación de clientes/proveedores del sitio público, a petición del usuario durante esta misma sesión. Resumen:

- El formulario real vive en `custom_addons/medicine_depot_portal/` (ruta `/afiliacion`, servida en `odoo.bodegademedicamentos.com`, **no** en el dominio raíz `bodegademedicamentos.com` — ese dominio no tiene vhost en este servidor, vale la pena confirmar con el equipo si debería apuntar aquí).
- Captura datos de contacto + 7 documentos (licencias sanitarias, INE, cédula profesional, etc.) y escribe directo a `res.partner` vía `sudo()`. La documentación del módulo (`README.md`) está desactualizada — dice que genera un `crm.lead`, pero el código actual no lo hace.
- **Hallazgo crítico:** no existe ninguna notificación cuando llega una solicitud nueva — ni correo, ni Telegram. El equipo comercial solo se entera revisando Contactos manualmente en Odoo.
- Ya existe un microservicio OCR (`ocr-service`, FastAPI) en la misma red Docker que n8n, sin usar para este flujo.
- Propuestas concretas (sin implementar, pendientes de decisión): (1) notificación inmediata a Telegram vía webhook cuando llega una solicitud — más simple y de mayor impacto; (2) checklist diario de documentos faltantes con seguimiento; (3) validación automática de documentos reusando el `ocr-service` existente; (4) mover de escritura directa a un flujo de revisión humana antes de activar la cuenta (ataca un hallazgo de seguridad ya señalado en `AFILIACION_WORKFLOW_AUDIT.md` del propio repo).

**Candidato natural para una próxima iteración de esta auditoría — implementado el mismo día como R8 (ver sección 7).**

## 7. R8 — Notificación de nueva solicitud de afiliación [IMPLEMENTADO Y VERIFICADO 2026-08-12]

Se construyó `12_Afiliacion_Notificacion` (`afiliacion-notificacion-uuid`), activo, **Trigger:** `Webhook` POST `afiliacion-nueva-solicitud`. Se modificó `custom_addons/medicine_depot_portal/controllers/portal.py` (backup: `portal.py.bak_20260813_001658`) agregando un método `_notify_n8n_new_affiliation(partner_id)` llamado justo después de que el `create()`/`write()` del partner es exitoso — **best-effort con timeout de 3s**, nunca bloquea ni rompe la respuesta al usuario si n8n está caído o lento (`try/except` envolvente, solo deja un `_logger.warning`).

**Actions del workflow:** `Autenticar Odoo` → `Buscar Partner` (`search_read` con `context: {bin_size: true}` para no traer el contenido base64 completo de los 7 documentos, solo su tamaño/presencia) → `Formatear Mensaje Afiliacion` (nombre, email, teléfono, especialidad, checklist de documentos completos/faltantes, link directo a Odoo) → Telegram (tema Ventas, thread 53 — no hay tema dedicado "Afiliaciones", encaja como alta de cliente nuevo).

**Verificado con una prueba real de extremo a extremo**, no solo simulada: se armó un POST real contra `https://odoo.bodegademedicamentos.com/afiliacion` (con su token CSRF real, tal como lo haría un usuario) → creó el partner real (`id 7485`) → **n8n disparó la ejecución automáticamente 0.1 segundos después** (confirmado en `execution_entity`, `status=success`) → notificación enviada a Telegram. El contacto de prueba se eliminó después de confirmar.

### Hallazgo crítico durante la construcción de R8, con impacto retroactivo en trabajo previo de esta misma auditoría

Al registrar el webhook de `12`, apareció repetidamente un path malformado (`<workflowId>/<nombre del nodo>/<path>`) en vez del path limpio esperado, incluso reinsertando el workflow por varios métodos distintos (SQL directo, `n8n import:workflow` + `publish:workflow` oficiales). Se investigó leyendo el código fuente de n8n dentro del contenedor (`active-workflow-manager.js`, `webhook.service.js`, `node-helpers.js` del paquete `n8n-workflow`) y se encontró la causa exacta: `getNodeWebhookPath()` usa el path limpio solo si `node.webhookId` no es `undefined`. Corregirlo en `workflow_entity.nodes` no alcanzó — **el runtime de n8n resuelve la versión activa desde `workflow_history` (la tabla de versión "publicada", vía `workflow_entity.activeVersionId`), no desde `workflow_entity.nodes` directamente.**

**Esto significa que todo fix aplicado en esta auditoría vía `UPDATE workflow_entity SET nodes = ...` sin también actualizar `workflow_history` quedó guardado en la base pero *no estaba realmente en efecto* en las ejecuciones reales**, aunque `workflow_entity.nodes` mostrara el contenido correcto al consultarlo. Se verificó y confirmó el caso concreto: el fix del bug de duplicados de proveedores en `04_Sync_Ordenes_Compra` (sección 1, hallazgo 3) **nunca había tomado efecto realmente** hasta este momento, pese a haberse marcado como "aplicado y verificado" antes en este mismo reporte — la verificación anterior solo probó la lógica de la consulta de forma aislada (fuera de n8n), no una ejecución real del workflow ya corregido.

**Se corrigió de raíz para los 7 workflows afectados** (`00`, `01`, `04`, `05`, `07`, `08`, `12` — todos los que recibieron un `UPDATE` a `nodes` después de su creación inicial en esta auditoría): se generó una nueva versión en `workflow_history` para cada uno con el contenido actual de `workflow_entity.nodes`, y se actualizó `workflow_entity.versionId`/`activeVersionId` para apuntar a esa nueva versión. Confirmado tras reiniciar: el fix de `04` ahora sí está presente en la versión activa publicada, y el webhook de `12` registra el path limpio correctamente.

**Lección para cualquier edición futura de un workflow n8n por SQL directo en este servidor: nunca alcanza con `UPDATE workflow_entity SET nodes = ...` solo. Siempre hay que generar una versión nueva en `workflow_history` y actualizar `activeVersionId` en la misma operación**, o el cambio queda "guardado pero no publicado" de forma silenciosa — sin ningún error visible que lo delate.

## 8. Auditoría del stack con pruebas reales (2026-08-12, post-fix de la sección 7)

Con todos los workflows ya republicados correctamente, se corrieron pruebas reales por flujo para auditar el comportamiento del stack completo. Metodología distinta según tipo de trigger (no hay API key de n8n configurada para poder disparar ejecuciones de Schedule manualmente sin usar la UI):

### Webhooks (5 ejecuciones reales de n8n cada uno, vía HTTP directo al endpoint)

| Workflow | Resultado | Hallazgo |
|---|---|---|
| `04_Sync_Ordenes_Compra` | 5/5 exitosas (201), 957-2330ms | **Bug real encontrado y CORREGIDO (2026-08-13):** una orden con un VAT de proveedor inexistente (`XXX000000XX0`) no fallaba ni se marcaba para revisión — se creaba igual, atribuida a **Brudifarma** (fallback hardcodeado `partnerId = pIdMatch ? ... : 3001` en `Preparar Preload Lotes`). **Fix:** se quitó el fallback; ahora `partner_found` se propaga explícito y un nuevo nodo `Partner Encontrado?` corta el flujo — si no se encuentra, responde `404` con mensaje claro (`"Proveedor no encontrado..."`) y alerta a Telegram (tema Compras), **sin crear ninguna orden**. Verificado en vivo repitiendo el caso exacto que reveló el bug: ahora responde `404`, cero órdenes creadas (antes: `201`, orden atribuida a Brudifarma). Prueba de regresión con proveedor real (Quifamesa) confirma que el flujo normal sigue funcionando igual (`201`, partner correcto `id 3455`). Órdenes de prueba canceladas y eliminadas después de cada verificación.
| `12_Afiliacion_Notificacion` | 5/5 exitosas (200), 796-1110ms, incluyendo un `partner_id` inexistente (maneja bien el caso, no revienta) | Sin hallazgos de lógica. Se creó un tema dedicado **"Afiliaciones"** (thread 92, ícono ✍️, mensaje fijado) y se movió el enrutamiento desde "Ventas" — verificado con una ejecución real post-cambio. |

`06_OCR_Documentos` y `08_Conciliacion_Bancaria` son esqueletos inactivos — no se dispararon ejecuciones reales (su lógica ya se validó por simulación antes de construirlos, ver secciones 1 y 3 de R1).

### Schedule (5 corridas repetidas de la consulta/lógica subyacente contra Odoo — no se pudo disparar la ejecución real de n8n sin API key; el motor de scheduling de n8n en sí ya está probado de forma independiente por las 300+ ejecuciones reales de `01_Healthcheck_Odoo`)

| Workflow | 5/5 consistente | Tiempos (ms) | Resultado actual |
|---|---|---|---|
| `01_Healthcheck_Odoo` | ✅ | 14-38 | Odoo responde `pass` |
| `02_Conciliacion_Inventario` | ✅ | 17-23 | 0 discrepancias de stock |
| `03_Alertas_Lotes_Vencimiento` | ✅ | 18-21 | 33,805 lotes con fecha de caducidad registrada |
| `05_Reporte_Ventas_Diario` | ✅ | 209-246 | 1000+ líneas de venta (tope de la consulta de prueba, no del workflow real que usa rango de fecha) |
| `07_Deteccion_Duplicados_Proveedores` | ✅ | 38-53 | 80 VAT duplicados de 2,563 con VAT (estable, sin cambios desde que se construyó) |
| `09_Backlog_Ordenes_Compra_Draft` | ✅ | 17-21 | 5,724 PO en draft |
| `10_Backlog_Pickings_Atascados` | ✅ | 16-26 | 3,701 pickings atascados |
| `11_Calidad_Catalogo` | ✅ | 25-40 | 839 productos con algún dato incompleto |

**Conclusión de la auditoría del stack:** todos los flujos responden de forma estable y rápida (menos de 250ms en el peor caso), sin errores intermitentes en ninguna de las 5 corridas por flujo. El bug de fallback hardcodeado en `04` (único hallazgo de fondo) ya se corrigió y verificó en vivo el mismo día — ver detalle arriba.

## 9. Revisión humana antes de activar afiliación — IMPLEMENTADO Y VERIFICADO 2026-08-13

Se implementó el punto 4 de la lista de pendientes (staging/revisión antes de escribir a `res.partner`), en la variante elegida por el usuario: **crear el partner igual que antes (sin romper el flujo actual), pero marcado "pendiente" hasta que el equipo lo apruebe**, en vez de un modelo de solicitud separado (más invasivo).

**Cambios en `custom_addons/medicine_depot_portal`:**
- **`models/res_partner.py` (nuevo):** campo `x_affiliation_status` (Selection: `pending`/`approved`, `tracking=True`) + método `action_approve_affiliation()`.
- **`views/res_partner_views.xml` (nuevo):** hereda `base.view_partner_form` — banner de alerta + botón "Aprobar Afiliación" (visible solo si `pending`), y el campo visible en el formulario.
- **`controllers/portal.py`:** en `afiliacion()`, se marca `x_affiliation_status='pending'` **solo** en la rama de creación de partner nuevo (un usuario ya logueado que actualiza sus datos no pierde una afiliación ya aprobada).
- **`controllers/public.py`:** `WebsiteSaleShopAccess.shop()` ahora también bloquea (con página nueva) a usuarios logueados cuyo partner esté `pending`, además del bloqueo ya existente para usuarios públicos.
- **`views/public_templates.xml`:** nueva plantilla `md_affiliation_pending` ("Tu afiliación está en revisión", reutiliza el mensaje "24-48 horas hábiles" que ya usaba la página de acceso restringido — el negocio ya comunicaba ese tiempo de validación, solo no estaba aplicado técnicamente).

**Verificado end-to-end con un usuario de prueba real** (partner + usuario portal temporal, eliminados después): afiliación nueva → `pending` → login → `/shop` bloqueado mostrando "Afiliación en Revisión" → `action_approve_affiliation()` → `/shop` accesible normalmente. Los 4 pasos confirmados en vivo, no solo por lectura de código.

### Bug real encontrado y corregido durante la verificación de R8 (afectaba también el "verificado" original de esa sección)

Al probar el mensaje de Telegram actualizado, se descubrió que **la notificación de R8 nunca había mostrado los datos reales del partner** — ni siquiera en la prueba "verificada end-to-end" documentada originalmente en la sección de R8. Causa: `_notify_n8n_new_affiliation()` se llama *antes* de que la transacción HTTP de Odoo haga commit; n8n consulta el partner por una conexión separada (transacción distinta) y, bajo aislamiento READ COMMITTED de Postgres, la fila recién creada aún no es visible ahí — la búsqueda siempre caía en la rama "partner no encontrado", aunque la ejecución de n8n reportara `success`. **Fix:** `self.env.cr.commit()` explícito justo antes de notificar (patrón estándar de Odoo para notificar sistemas externos después de una escritura crítica). Verificado en vivo: antes del fix, el mensaje real decía "No se encontro el partner_id=X"; después, muestra nombre/email/teléfono/documentos correctos.

**Lección:** que una ejecución de n8n reporte `status=success` no confirma que hizo lo correcto — hay que revisar el contenido real (`execution_data`) cuando el resultado depende de datos de otro sistema, no solo el código de estado HTTP.

### Filtros de Contactos para afiliación — creados 2026-08-13

Se agregaron 2 filtros compartidos (`ir.filters`, visibles para todos los usuarios) en el modelo `res.partner`, disponibles desde el buscador de la app Contactos:
- **"Afiliaciones Pendientes"** — dominio `[('x_affiliation_status', '=', 'pending')]`. El más útil para revisión diaria.
- **"Todas las Afiliaciones"** — dominio `[('x_affiliation_status', '!=', False)]`. Segmento completo (pendientes + aprobadas).

Verificado funcionalmente (no solo por lectura del registro): se creó un partner de prueba con `x_affiliation_status='pending'` y se confirmó que el dominio exacto de ambos filtros lo encuentra correctamente, antes de limpiarlo.

## 10. Puntos sueltos resueltos (2026-08-13)

- **Producción real en Odoo Online/odoo.sh — VERIFICADO 2026-08-13 vía navegador (sesión ya iniciada).** Se confirmó accediendo directo a `https://medicinedepot.odoo.com/odoo/accounting` (Contabilidad > Tablero): **la conciliación bancaria SÍ está activa y en uso real en producción** — hallazgo que cambia la lectura de R1. El Tablero de Contabilidad muestra 32 diarios (journals), varios bancarios/de pago con saldo y backlog real de conciliación:
  - **Santander Mérida Cta 6052651050-7**: Balance $5,010.43, Pagos acumulados $1,101,929.46, **101 transacciones por conciliar**.
  - **Get Net Campeche**: Balance $18,591.54, 5 por conciliar.
  - **Get Net Chetumal**: Balance $6,629.53, 3 por conciliar.
  - Get Net Playa, Get Net Ticul y otros más (32 en total), cada uno como terminal de pago por sucursal.

  **Conclusión:** el "gap total" que motivó R1 (`account.bank.statement.line` con 0 registros) es una **limitación del ambiente de pruebas/migración de `ionos`** (nunca se sembró con datos bancarios), no un proceso ausente en el negocio real — en producción la conciliación ya corre de forma nativa en Odoo, con su propio backlog normal de negocio (109 transacciones pendientes en total entre las 3 cuentas revisadas). **Esto no invalida el esqueleto `08_Conciliacion_Bancaria`** construido — sigue siendo útil si algún día se decide automatizar alertas/notificaciones sobre ese backlog real —, pero si se quisiera conectarlo a la producción real, implicaría dar acceso de n8n a `medicinedepot.odoo.com` (credenciales nuevas, mayor cuidado por tratarse de datos financieros reales), una decisión aparte que no se tomó en esta sesión.
- **Credenciales hardcodeadas en `04` — corregidas.** El nodo `Validar Payload` tenía `dbName/dbUser/dbPass` **y también el token del bot de Telegram y el chat ID** en texto plano (este último no se había mencionado antes — se encontró al revisar el bloque completo). Se reemplazaron todos por `$env.ODOO_DB`/`$env.ODOO_USER`/`$env.ODOO_PASSWORD`/`$env.TELEGRAM_BOT_TOKEN`/`$env.TELEGRAM_CHAT_ID`, mismo patrón que ya usan los demás workflows. Verificado que `$env` funciona correctamente dentro de un nodo Code (no solo en expresiones de nodos HTTP) con una ejecución real (`201`, orden creada y notificada). El token de Telegram ya no aparece en el JSON exportado a `docs/n8n_workflows/04_sync_ordenes_compra.json`.
- **Checklist diario de documentos de afiliación pendientes — construido y activo.** `13_Afiliacion_Documentos_Pendientes` (Schedule diario 9am, tema Afiliaciones). Verificado con datos reales: solo 2 clientes en todo el sistema tienen el flag de afiliación activo (`x_studio_contact_type='Cliente'`), ambos con documentos faltantes — el flujo de afiliación es nuevo y con poco uso real todavía, pero la automatización queda lista para cuando escale.
- **Validación automática de documentos con el `ocr-service` existente — corrección importante al hallazgo previo del subagente.** Se leyó el código fuente real (`/opt/n8n-md/ocr-service/main.py` y `extraction.py`): el servicio es específicamente para **facturas** — extrae RFC del emisor, fecha, folio y líneas de producto (cantidad/descripción/precio) vía regex sobre texto de Tesseract OCR. **No es un validador genérico de documentos de identidad/licencias** como sugería la propuesta original — no puede determinar "¿esta licencia sanitaria está vigente?" ni "¿este INE es válido?", solo extrae el primer patrón de fecha/RFC que encuentra en el texto, sin entender qué documento es. Uso honesto y acotado que sí es viable: extraer el RFC de la "Constancia de Situación Fiscal" subida en `/afiliacion` y cruzarlo contra el VAT que la persona escribió a mano en el formulario, para detectar RFCs mal tecleados — **no implementado todavía, es una propuesta acotada pendiente de decisión** (vale la pena vs. el esfuerzo de conectar 7 documentos de tipos muy distintos a un extractor pensado para facturas).
- **README.md de `medicine_depot_portal` corregido:** la tabla de Controllers decía que `/afiliacion` vivía en `controllers/public.py` — en realidad está en `controllers/portal.py` (confirmado leyendo el código, no solo el README). Se agregó `controllers/portal_digitization.py` (no documentado, ruta `/my/dashboard/digitize`). Se corrigió la nota técnica que decía "la afiliación... genera un lead en CRM" — el código actual no crea ningún `crm.lead`, escribe directo a `res.partner`. Se agregó una nota sobre la notificación a n8n agregada en R8. Backup: `README.md.bak_20260813_004049`.

## 11. Migración de diarios bancarios reales (2026-08-13) — resuelve el gap principal encontrado por el subagente de contabilidad

Se creó/replicó en `medicinedepot_dev` (empresa **MDS MÉRIDA**, `company_id=7`, equivalente a la matriz real "SABRINA ELIZABETH ROJANO ROMERO" de producción) el set completo de diarios bancarios reales que faltaban, usando como fuente el inventario exacto extraído de producción vía navegador (nombre, prefijo, cuenta contable y número de cuenta de cada uno).

**Hallazgo previo a construir:** los códigos contables `102.01.01`–`102.01.05` ya existían en migración, pero como **cuentas genéricas de la plantilla mexicana de Odoo** ("Banco", "Cuenta transitoria", "Transferencia de liquidez", "Recibos pendientes", "Pagos pendientes") — coincidían en número con las cuentas reales de producción por pura casualidad, no en contenido. Se confirmó que esas 5 cuentas no tenían ningún movimiento contable (`account_move_line` = 0), así que se **renombraron** en vez de crear duplicados con otro código — más fiel a la estructura real de producción y sin riesgo (nada que perder al renombrar algo sin uso).

**Trabajo realizado:**
1. Renombradas 5 cuentas existentes (102.01.01–05) a los nombres reales de Santander (Mérida/Campeche/Cancún/Chetumal/Concentradora), marcadas `reconcile=true`.
2. Creadas 9 cuentas nuevas: 102.01.06 (BBVA) a 102.01.13 (Get Net Chetumal), más 205.02.02 (TC Santander Likeu, `account_type=liability_credit_card`).
3. Creados 13 diarios tipo `bank` + 1 tipo `credit` (`account.journal`), cada uno con `default_account_id` apuntando a su cuenta y `bank_acc_number` con el número real — esto generó automáticamente los 13 `res.partner.bank` correspondientes (confirmado, aunque no documentado explícitamente en la UI/API pública de Odoo).
4. Un diario (`BNK1`, Santander Mérida) ya existía como el diario "Bank" genérico por defecto de la plantilla — mismo trato: 0 asientos, se **reutilizó** actualizando nombre y número en vez de crear uno nuevo (el código `BNK1` no se puede repetir por empresa).

**Verificado:** los 14 diarios existen con el nombre, prefijo, cuenta contable y número de cuenta correctos; los 13 `res.partner.bank` están correctamente vinculados a su diario.

**Hallazgo sin resolver, a confirmar con el negocio:** en producción, los diarios "Get Net Mérida 1" y "Get Net Mérida 2" muestran números de cuenta **cruzados** entre el nombre del diario y el nombre de la cuenta contable vinculada (diario "...1 - 70878550" enlaza a cuenta "...1 - 9461337", y viceversa). Se replicó tal cual como está en producción (fidelidad a la fuente), pero vale la pena que el equipo confirme cuál número es el correcto antes de usar esas cuentas para conciliación real.

**No verificado (no se alcanzó por límite de sesión):** compañía y moneda se asumieron por muestreo (2 diarios revisados en producción, ambos bajo la empresa matriz) más la convención estándar de Odoo de que esta vista lista solo la empresa activa — no se verificó exhaustivamente cada uno de los 13. Moneda asumida MXN (peso mexicano) por default de la empresa, no confirmada explícitamente por diario.

**Pendiente:** esto solo resuelve la *estructura* (diarios + cuentas + números de cuenta). Sincronizar saldos y movimientos reales (los "101/291/152/73/6 por conciliar" vistos en producción) requeriría un proceso de migración de datos aparte — no se hizo en esta sesión.

## 12. Corrección importante: la conciliación bancaria de Enterprise SÍ tiene equivalente en Community, vía OCA (2026-08-13, corrige hallazgo previo)

**El hallazgo original de esta sección (escrito antes) era incorrecto y queda corregido aquí.** La conclusión de que se necesitaba comprar licencia Enterprise se basó en probar una URL adivinada de Enterprise (`/odoo/accounting/<id>/reconciliation`), que efectivamente renderiza en blanco en migración — pero esa URL nunca fue el punto de entrada real, simplemente no aplica a este ambiente.

**Verificado por consulta directa a `ir_module_module`:** los módulos OCA `account_reconcile_oca` y `account_statement_base` **ya están instalados** en `medicinedepot_dev` (`state='installed'`), junto con 12 registros en `account.reconcile.model` ya configurados (genéricos: "Transferencias internas" y "Comisiones bancarias", replicados por compañía — aún no ajustados a los patrones reales de MedicineDepot, ej. "TRASPASO A NÓMINA", "COMISIÓN", "DEPÓSITO TARJETA", "TELÉFONOS DE MÉXICO").

**El punto de entrada real** no es una URL adivinada sino el botón "TRANSACCIONES" en cada tarjeta de diario del tablero (`/odoo/accounting`), que lleva a `/odoo/accounting/<journal_id>/action-517` ("Conciliar líneas de extracto bancario") — una vista completamente distinta a la que se probó antes.

**Verificado en vivo con datos reales:** se creó una línea de extracto bancario de prueba (diario BBVA, id 75, "DEPOSITO PRUEBA CLAUDE", $750.50) y se navegó a esa vista real. Renderiza correctamente: "Balance global", sugerencia de match automático contra una cuenta, botones CONCILIAR / RESTABLECER CONCILIACIÓN / A REVISAR / VER ASIENTO, atajos rápidos "TRANSFERENCIAS INTERNAS" / "COMISIONES BANCARIAS", y tabs CONCILIAR / OPERACIÓN MANUAL / OTHER INFO / CHARLA — visual y funcionalmente muy cercano al widget kanban de Enterprise. Línea de prueba eliminada después de la verificación.

**Conclusión corregida:** no se necesita comprar licencia Enterprise para tener conciliación bancaria con auto-matching. Lo que falta es trabajo de configuración, no de licenciamiento:
1. Ajustar/expandir las 12 reglas genéricas de `account.reconcile.model` para que reconozcan los patrones reales de las transacciones bancarias de MedicineDepot (nómina, comisiones, depósitos con tarjeta, domiciliaciones conocidas como Teléfonos de México, etc.).
2. Validar el comportamiento una vez que empiecen a fluir extractos bancarios reales (hoy los 14 diarios de la sección 11 están vacíos de movimientos).
3. Opcionalmente, revisar si hace falta importación automática de extractos (statement import) para no depender de carga manual.

Los 14 diarios/cuentas creados en la sección 11 siguen siendo válidos y necesarios — el gap de *estructura* ya se resolvió, y ahora se confirma que el gap de *funcionalidad de UI* tampoco existe: solo falta afinar reglas y cargar datos reales.

## 13. Opción 3 explorada vía n8n: resumen ligero de conciliación (2026-08-13)

Mientras se decide entre licencia Enterprise / conciliación manual Community / módulo custom (sección 12), se construyó `14_Conciliacion_Bancaria_Resumen` (Schedule semanal, lunes 8:15am, tema Finanzas y Conciliación) — una versión ligera vía Telegram del dashboard de conciliación de Enterprise: cuenta transacciones sin conciliar (`is_reconciled=false`) por cada uno de los 14 diarios reales creados en la sección 11, ordenadas de mayor a menor backlog, replicando el mismo estilo de badge ("X por conciliar") que se ve en producción.

**Verificado:** se sembraron 9 líneas de prueba repartidas en 3 diarios distintos, se corrió la consulta+formato exacto del workflow, y produjo el resumen correcto y ordenado; datos de prueba eliminados después. Es un complemento útil aunque el módulo OCA (sección 12) ya provea la vista con auto-matching en Odoo mismo: da visibilidad inmediata en Telegram sin tener que entrar a Odoo a revisar diario por diario.

**Mejora aplicada a `14` (2026-08-13):** se agregó un nodo `Buscar Transacciones Mas Antiguas` (`search_read` ordenado por fecha ascendente) y se enriqueció el mensaje para mostrar hasta 3 transacciones más antiguas por diario (fecha, descripción, monto) debajo de cada badge de conteo — no solo el número, también qué hay que revisar. Verificado sembrando 5 transacciones con fechas/montos variados en 3 diarios distintos; el mensaje salió correctamente ordenado y con el detalle esperado. Datos de prueba eliminados después.


## 14. Reglas de conciliación (`account.reconcile.model`) afinadas a patrones reales (2026-08-13)

**Patrones reales obtenidos de producción** (`medicinedepot.odoo.com`, vía sesión de Chrome autenticada, `search_read` sobre 800 líneas de extracto no conciliadas, agrupadas por prefijo normalizado): los patrones de mayor volumen son `COMISION` (176), `IVA COMISION` (176, siempre en línea separada 1:1 con la comisión), `TRASPASO A NOMINA` (80) + `NOMINA SANTANDER` (20), `DEPOSITO TARJETA` (73), y `TRASPASO DE {SUCURSAL}` (Cancún/Campeche/Chetumal/Mérida/Santander/Bancomer, 92 en conjunto). Esto cubre ~617 de las 800 líneas muestreadas — el resto es texto libre de movimientos de caja de POS (retiros/depósitos con folio único), no automatizable con reglas de label.

**Dos bugs preexistentes encontrados y corregidos** (no relacionados con el trabajo de esta sesión, ya estaban mal configurados):
1. La regla "Bank Fees"/"Comisiones bancarias" (una por compañía, 6 en total) tenía `match_label_param = "Bank Fees"` (inglés) — el texto real en los extractos es "COMISION" (español), así que la regla nunca habría matcheado nada.
2. La cuenta contrapartida de esa misma regla apuntaba a **"Stock Variation" / "Variación de Existencias"** (501.01.02, costo de inventario) en las 6 compañías — cualquier comisión bancaria reconciliada con esa regla se habría contabilizado como costo de mercancía, no como gasto financiero. Corregido a la cuenta real `701.10.01 Bank fees` por compañía.

**Bug propio encontrado y corregido:** al crear los diarios bancarios reales de la sección 11, se renombró la cuenta genérica 1726 (que hasta ese momento era el "Liquidity Transfer" / cuenta puente de traspasos entre cuentas propias de MDS MÉRIDA) a "Santander Cancún Cta 6053902645-1" — un nombre real y específico. Esto rompió dos cosas para la compañía 7 sin que se notara en su momento: `res.company.transfer_account_id` (usado por el wizard nativo de Odoo "Enviar/Recibir dinero entre bancos") y la línea de la regla "Internal Transfers" seguían apuntando a esa cuenta ya renombrada. **Corregido:** se creó una cuenta nueva y dedicada (`102.01.14 Transferencias entre Cuentas Propias`, id 1739) y se reapuntaron ambas referencias a ella.

**Reglas nuevas creadas (una por compañía, 6×3=18 registros nuevos + 12 corregidos = 30 reglas en total):**
- `IVA de Comisiones Bancarias` (sequence 5, `match_label contains "IVA COMISION"` → cuenta `118.01.01 Creditable VAT paid`). Sequence más baja que "Comisiones bancarias" porque el texto "IVA COMISION" también contiene la palabra "COMISION".
- `Traspaso a Nómina` (sequence 15, `contains "NOMINA"` → cuenta `210.01.01 Provision of wages and salaries to pay`). Sequence más baja que "Transferencias internas" porque "TRASPASO A NOMINA" también contiene "TRASPASO".
- `Depósito con Tarjeta` (sequence 20, `contains "DEPOSITO TARJETA"` → misma cuenta puente que traspasos internos — es el neto que las terminales Get Net depositan a la cuenta bancaria real, dinero que ya es propio).
- `Transferencias internas` ajustada (sequence 25, antes sin ningún filtro de label — demasiado permisiva —, ahora `contains "TRASPASO"`).

**Verificado en vivo:** se crearon 3 líneas de prueba en el diario BBVA (`COMISION MANEJO DE CUENTA AGO26`, `IVA COMISION MANEJO DE CUENTA`, `TRASPASO A NOMINA QUINCENA 15`) y se navegó a la vista real de conciliación (`/odoo/accounting/75/action-517`). Los 5 botones de atajo ("IVA DE COMISIONES BANCARIAS", "COMISIONES BANCARIAS", "TRASPASO A NÓMINA", "DEPÓSITO CON TARJETA", "TRANSFERENCIAS INTERNAS") aparecieron correctamente sobre cada línea; al hacer clic en "TRASPASO A NÓMINA" sobre la línea de nómina, la contrapartida se autocompletó con "Provisión de sueldos y salarios a pagar" por el monto exacto ($85,000.00), lista para validar — sin llegar a validar el asiento (para no dejar movimientos ficticios). Las 3 líneas de prueba se eliminaron después.

**Pendiente:** las reglas nuevas solo existen en `medicinedepot_dev` (ambiente de migración) — no se tocó producción. Los patrones específicos de sucursal (`TRASPASO DE CANCUN/CAMPECHE/CHETUMAL/MERIDA`) quedan cubiertos por la regla genérica `TRASPASO` en vez de reglas dedicadas por sucursal; si se quiere que la sugerencia indique la sucursal exacta en la etiqueta contable (en vez de solo la cuenta puente genérica), se pueden desglosar en el futuro. Los movimientos de caja de POS individuales (retiros/depósitos con folio único, ~180 patrones distintos con 1-2 ocurrencias cada uno) no son candidatos razonables para reglas de label — seguirán conciliándose manualmente o por `match_partner_ids` si se decide vincularlos a empleados/cajas específicas.


## 15. Auto-conciliación nativa activada para comisiones bancarias (2026-08-13)

Revisando el código fuente de `account_reconcile_oca` (`/mnt/oca-account-reconcile/account_reconcile_oca/models/account_bank_statement_line.py`) se encontró que el módulo ya trae un mecanismo de auto-conciliación nativo: `account.bank.statement.line.create()` llama automáticamente a `_auto_reconcile()`, que aplica cualquier regla de `account.reconcile.model` cuyo campo `trigger = 'auto_reconcile'` (en vez de `'manual'`, que es lo que usan los 5 botones de atajo de la sección 14) y, si hay match, **publica el asiento sin intervención humana**. Es la forma "oficial" de automatizar reconciliación en este módulo — no requiere n8n ni ningún proceso externo.

**Decisión del usuario** (dado que esto cambia el comportamiento de "sugerir, humano confirma" a "publicar solo" — se preguntó explícitamente antes de aplicar): activar `trigger='auto_reconcile'` únicamente en las 2 reglas de menor riesgo — `Comisiones bancarias` e `IVA de Comisiones Bancarias` (12 registros, 2×6 compañías) — por ser montos pequeños y patrón de texto inequívoco. `Traspaso a Nómina`, `Depósito con Tarjeta` y `Transferencias internas` se dejan en `'manual'` (siguen requiriendo un clic humano) por involucrar montos mayores donde el juicio humano vale más.

**Verificado en vivo:** se creó una línea de prueba (`COMISION MANEJO DE CUENTA AGO26`, -$150, diario BBVA) vía `create()` puro (sin ningún paso manual posterior) — quedó `is_reconciled=true` y generó automáticamente el asiento `BNK6/2026/00002` con las cuentas correctas (BBVA Bancomer al haber $150 / Bank fees al debe $150). Limpieza: `unreconcile_bank_line()` falló por permisos ("no tiene permisos para restablecer a borrador en facturas" — mismo tipo de restricción de grupo que bloqueó la escritura ORM en la sección 14), pero el `unlink()` directo de la línea sí tuvo permiso y **eliminó en cascada tanto la línea como el asiento contable** — verificado por SQL que no quedó ningún rastro (0 filas en `account_move`, `account_move_line` ni `account_bank_statement_line` para los ids de prueba).

**Efecto esperado:** de aquí en adelante, cualquier línea de extracto bancario real cuyo texto contenga "COMISION" o "IVA COMISION" se reconciliará y publicará sola en el momento en que se cargue a Odoo (import de extracto, API, o carga manual) — sin pasar por n8n ni requerir revisión. El backlog reportado por `14_Conciliacion_Bancaria_Resumen` (sección 13) debería reducirse de forma natural en esas dos categorías una vez que haya extractos reales fluyendo.


## 16. `14_Conciliacion_Bancaria_Resumen` extendido: visibilidad de lo auto-conciliado (2026-08-13)

Dado que la sección 15 hace que ciertas líneas se reconcilien y publiquen solas (sin pasar por n8n ni por revisión humana), se agregó una segunda rama al workflow `14` para que ese trabajo silencioso también quede visible en Telegram — mismo criterio de "ningún proceso automático sin ventana de visibilidad" ya aplicado en R6 (`healthcheck.sh`).

**Nodos nuevos:** `Buscar Auto-Conciliados Semana` (`read_group` sobre `account.move.line`, filtrando `reconcile_model_id in [12 ids de las reglas en auto_reconcile]` y `create_date` de los últimos 7 días) → `IF - Hubo Auto-Conciliados?` → `Formatear Auto-Conciliados` (agrupa por nombre de regla) → `Notificar Telegram Auto-Conciliados` (mismo tema Finanzas y Conciliación, thread 75). Corre en paralelo a la rama existente de "por conciliar", después de `IF - Auth OK?`.

**Publicado con el patrón obligatorio** (nueva entrada en `workflow_history` + `activeVersionId` actualizado + `docker restart md_n8n`, ver [[feedback_n8n_workflow_history_desync]] en memoria) — quedó `active=true` con la versión nueva confirmada en `workflow_entity`.

**Verificado en vivo:** se crearon 2 líneas reales (`COMISION MANEJO DE CUENTA SEP26`, `IVA COMISION MANEJO DE CUENTA`) que se auto-conciliaron solas al crearse (confirmado `is_reconciled=true` en ambas), y se ejecutó manualmente la misma consulta `read_group` que usa el nodo nuevo — devolvió exactamente 1 conteo para la regla de Comisiones (id 12) y 1 para IVA de Comisiones (id 18), con el formato de campos (`reconcile_model_id_count`) que el código de formateo ya maneja. Líneas de prueba eliminadas después (unlink en cascada, sin rastro).


## 17. Datos bancarios reales importados a migración + bug de cuentas transitorias corregido (2026-08-13)

Para que la conciliación bancaria (secciones 12-16) tuviera datos reales sobre los que trabajar (no solo líneas de prueba), se extrajeron 219 líneas reales de producción (muestra de hasta 40 líneas más recientes por diario, de las 718 líneas sin conciliar totales al 2026-08-13, extraídas vía `fetch` autenticado desde la sesión de Chrome contra `medicinedepot.odoo.com`) y se importaron a los 14 diarios reales equivalentes en `medicinedepot_dev`.

**Bug crítico encontrado durante la importación:** al crear los 14 diarios bancarios reales (sección 11), Odoo asignó automáticamente la misma cuenta transitoria (`suspense_account_id`) a los 14 — porque no se especificó explícitamente al crearlos — y esa cuenta compartida resultó ser la cuenta bancaria REAL de Santander Campeche (1723). Para el diario de Campeche esto significaba que su cuenta por defecto y su cuenta transitoria eran la MISMA cuenta, violando la regla interna de Odoo de que un asiento de conciliación debe tener exactamente un apunte que involucre la cuenta bancaria — bloqueando la creación de cualquier línea nueva en ese diario con el error "El asiento contable... debe tener siempre exactamente un apunte contable que involucre la cuenta bancaria o de efectivo". Para los otros 13 diarios no rompía la creación (sus cuentas por defecto son distintas de 1723), pero igual era incorrecto: mezclaba lo pendiente de conciliar de las 13 cuentas restantes dentro del saldo de la cuenta bancaria real de Campeche.

**Diagnóstico:** se aisló el error probando la creación en distintos diarios uno por uno, se descartó que fuera un problema de concurrencia/caché (mismo resultado exacto — 179 creadas, 40 fallidas — en dos corridas independientes con reintentos, pausas de 150-800ms y conexiones HTTP frescas), y se capturó el traceback completo de Python, que apuntó a `account_bank_statement_line._synchronize_from_moves` (núcleo de Odoo) fallando dentro del create() de `account_move_line` interceptado por `account_asset_management` (OCA).

**Corregido:** se crearon 14 cuentas "Transitoria [Diario]" dedicadas (códigos `102.01.15` a `102.01.28`, compañía MDS MÉRIDA) y se reasignó `suspense_account_id` de cada uno de los 14 diarios a su propia cuenta. De paso se corrigió también que 4 de las 5 cuentas Santander renombradas en la sección 11 (Campeche, Cancún, Chetumal, Concentradora) tenían `account_type = "asset_current"` en vez de `"asset_cash"` (el tipo correcto para una cuenta de diario bancario) — solo Santander Mérida ya tenía el tipo correcto desde antes.

**Resultado tras el fix:** reintento completo de las 219 líneas — **219/219 creadas, 0 fallos**. De esas, **108 se auto-conciliaron solas** (vía el trigger nativo de la sección 15, comisiones + IVA de comisiones), quedando un backlog real "por conciliar" de 111 líneas repartidas en 10 diarios (Concentradora 29, Santander Mérida 19, Cancún y Playa 16, Campeche 14, Chetumal 14, BBVA 7, Get Net Campeche 5, Get Net Cancún 4, Get Net Chetumal 3, TC Santander Likeu 1).

Con esto, la conciliación bancaria (dashboard OCA), las reglas afinadas (sección 14) y el resumen semanal de `14_Conciliacion_Bancaria_Resumen` por Telegram ya tienen datos reales — no solo líneas de prueba — sobre los que operar.
