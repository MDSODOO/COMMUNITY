# Fase 3 -- Instrumentación de latencia real (local_ai_connector)

Diseño + código listo para revisión. **Nada de esto se aplicó contra
`ionos`** (ni escritura de archivos en el servidor, ni `ALTER TABLE`, ni
`-u`, ni restart de contenedores) -- eso queda para que el usuario lo
revise y decida. Todos los archivos de esta carpeta terminan en
`.propuesto` cuando reemplazan un archivo existente del módulo, salvo la
carpeta `migrations/` (que es nueva, y sí lleva el nombre final que tendría
en el repo).

## Problema que resuelve

No hay ninguna métrica de latencia persistida en producción. Las tablas
`local_ai_query_log` y `local_ai_image_quote_image` guardan estado y
`error_message`, pero nunca cuánto tardó la llamada a Ollama. Los únicos
tiempos conocidos (76s-242s del PoC de julio, 148.75s de la prueba del
31/07) son de pruebas puntuales manuales, no de tráfico real. Además hay un
patrón sin explicar: 2 de 17 `local_ai_image_quote_request` fallaron con
"Huerfano: proceso Odoo termino antes de completar la inferencia" -- un
mensaje que **no existe en el código actual** (se confirmó con
`grep -rn "Huerfano" custom_addons/local_ai_connector/` → sin resultados),
o sea que hoy esa nota vive solo como texto manual en la BD, sin ningún
dato automático que permita correlacionarla con un restart/deploy real.

## Archivos de esta carpeta

```
fase3_instrumentacion/
├── README.md                                   (este archivo)
├── __manifest__.py.propuesto                   version 19.0.1.1.0 -> 19.0.1.2.0
├── models/
│   ├── ai_query_log.py.propuesto               + duration_seconds
│   ├── image_quote_image.py.propuesto          + duration_seconds
│   └── image_quote_request.py.propuesto        + processing_started_at, processing_pid,
│                                                  _detect_orphaned_processing()
├── services/
│   ├── ollama_client.py.propuesto              generate_structured() ahora mide y devuelve
│   │                                            (parsed, duration_seconds)
│   ├── image_quote_processor.py.propuesto       consume la tupla, escribe duration_seconds,
│   │                                            escribe processing_started_at/pid + commit
│   │                                            antes de la llamada bloqueante, llama al
│   │                                            barrido de huérfanos
│   └── inventory_nl_resolver.py.propuesto        propaga duration_seconds en el dict de retorno
└── migrations/19.0.1.2.0/post-migrate.py       solo verifica (SELECT), no hace DDL propio
```

`controllers/ai_api.py` **no cambia** -- `log_query()` ya recibe el dict
`result` completo, y ahora ese dict trae `duration_seconds` gracias al
cambio en `inventory_nl_resolver.py`.

## 1. Diseño: cómo se mide la duración

`ollama_client.generate_structured()` es el único lugar que hace el
`requests.post` real hacia Ollama, en dos ramas:

- **Texto** (`priority='high'`): dentro de `with _inference_lock:`, un solo
  `requests.post` sin reintentos.
- **Visión** (`priority='low'`): dentro de `_call_ollama_with_retry()`, que
  puede reintentar hasta 3 veces con backoff exponencial (1s, 2s, 4s...),
  después de adquirir un advisory lock de Postgres (hasta 300s de espera).

**Decisión de diseño clave** (pedida explícitamente en el encargo): medir
solo el `requests.post` en sí, con `time.monotonic()` justo antes/después
de esa llamada -- no el método completo. Se excluye a propósito:

- la espera del advisory lock (`_acquire_ollama_lock`, hasta 300s),
- el backoff entre reintentos fallidos,
- el parseo de JSON de la respuesta,
- cualquier trabajo posterior del caller (matching de producto, etc.).

Motivo: si se mide el método completo, la cifra mezcla "cuánto tarda el
modelo en inferir" con "cuánto tiempo esperamos turno por el lock/otros
workers" -- dos causas y remedios distintos. Con la medición angosta,
`duration_seconds` es comparable entre corridas y sirve para detectar
degradación real del modelo/host (ver `ollama_client.py.propuesto`, tiene
el detalle exacto documentado en el docstring del módulo).

En `_call_ollama_with_retry`, la duración es la del intento que **tuvo
éxito** (el último), no la suma de reintentos fallidos -- esos ya quedan
visibles en los `_logger.warning` existentes.

### Cambio de contrato (rompe compatibilidad, controlado)

`generate_structured()` pasa de devolver `parsed` a devolver
`(parsed, duration_seconds)`. Hay exactamente **2 call sites** en todo el
módulo (confirmado con `grep -rn "generate_structured" custom_addons/local_ai_connector/`):

- `services/inventory_nl_resolver.py`
- `services/image_quote_processor.py`

Ambos están actualizados en esta carpeta. Si en el futuro se agrega un
tercer caller sin mirar este cambio, Python fallará de forma ruidosa
inmediatamente (`ValueError: too many values to unpack` o similar) --no
hay riesgo de que un caller viejo lea silenciosamente la tupla como si
fuera el dict/list de siempre.

### Limitación conocida (documentada, no resuelta en esta fase)

Si la llamada a Ollama **falla** (`OllamaError`/`OllamaBusyError`), no hay
tupla que devolver -- no se captura cuánto tiempo pasó hasta el fallo. Los
campos `duration_seconds` quedan en `0.0` (default de `Float` en Odoo) para
esos casos, que **no es un cero real**, es "no disponible". Se documentó
así en los `help=` de los campos nuevos. Si más adelante hace falta
distinguir "0 real" de "no disponible", el cambio es menor (usar
`False`/`None` en vez de `0.0` al escribir) porque Postgres ya admite NULL
en columnas `float8`; no se hizo en esta fase para no ampliar el alcance
sin necesidad.

## 2. Campos nuevos, por modelo

| Modelo | Campo | Tipo | Se escribe en |
|---|---|---|---|
| `local.ai.query.log` | `duration_seconds` | Float | `models/ai_query_log.py` → `log_query()`, desde `result.get("duration_seconds")` |
| `local.ai.image.quote.image` | `duration_seconds` | Float | `services/image_quote_processor.py` → `_process_request()`, al hacer `image.write(...)` tras la llamada a Ollama |
| `local.ai.image.quote.request` | `processing_started_at` | Datetime | `services/image_quote_processor.py` → `process_next_pending_request()`, junto con `state='processing'`, **con commit inmediato antes de la llamada bloqueante** |
| `local.ai.image.quote.request` | `processing_pid` | Integer (`os.getpid()`) | mismo punto que arriba |

No se tocó `local.ai.image.quote.attempt` (es rate limiting, no tiene
relación con inferencia) ni se agregó nada a `local.ai.image.quote.line`
(no hace llamadas a Ollama).

## 3. Diseño: caso "Huérfano"

No se intenta resolver la causa raíz (podría seguir siendo la hipótesis de
restart/deploy coincidiendo con el cron, no confirmado). Se deja
instrumentado para la próxima vez:

1. **Contexto de intento** (`processing_started_at`, `processing_pid`): se
   escriben y se hace `env.cr.commit()` **antes** de entrar a la parte
   bloqueante (`_process_request`, que incluye la llamada a Ollama). Si el
   proceso de Odoo muere a medias (ej. `docker restart`), esos dos campos
   quedan en Postgres con datos reales aunque el resto de la transacción
   nunca se complete -- eso es exactamente lo que hoy falta para poder
   correlacionar un caso "huérfano" con `docker logs
   medicinedepot_dev_odoo` / eventos de restart alrededor de esa hora.

2. **Barrido automático** (`_detect_orphaned_processing`, en
   `models/image_quote_request.py.propuesto`, mismo patrón `_gc_*` que ya
   usa `local.ai.image.quote.attempt._gc_old_attempts`): al inicio de
   `process_next_pending_request`, busca solicitudes en `state='processing'`
   cuyo `processing_started_at` sea más viejo que
   `ORPHAN_PROCESSING_THRESHOLD_SECONDS` (900s = `VISION_TIMEOUT` (450s) +
   espera máxima del advisory lock (300s) + margen (150s)). Las marca
   `state='error'` con un mensaje que incluye el PID, el timestamp de
   inicio y los segundos transcurridos -- así, la próxima vez que ocurra,
   el `error_message` trae contexto real para investigar en vez de una
   nota manual sin datos. **No reintenta automáticamente** la solicitud
   (no sabemos en qué paso exacto se quedó, y reintentar a ciegas una
   llamada de 90-240s de CPU podría agravar el problema de recursos que ya
   documenta el propio módulo).

   Por qué a nivel de `local.ai.image.quote.request` y no de
   `local.ai.image.quote.image`: el patrón "huérfano" observado (2 de 17)
   está en la tabla `local_ai_image_quote_request`, y es ahí donde el
   `state='processing'` queda colgado sin que nada vuelva a recogerlo (el
   cron solo busca `state='pending'`). El nivel de imagen ya tiene su
   propio dato de latencia (`duration_seconds`) para el caso de éxito.

## 4. Migración

El proyecto usa la convención estándar de Odoo
(`migrations/<version>/{pre,post}-migrate.py`) -- se confirmó revisando
`migrations/19.0.1.1.0/post-migrate.py` (única migración existente en el
módulo, usada para `CREATE EXTENSION unaccent/pg_trgm`, algo que el ORM no
puede hacer solo).

**Esta fase no lo necesita para el DDL en sí**: los 5 campos nuevos son
`Float`/`Datetime`/`Integer` simples, sin `required=True`, sin default
distinto al que Odoo ya usa por tipo -- el propio ORM los agrega solo
(`ALTER TABLE ... ADD COLUMN`) al cargar el módulo con `-u`. Por eso
`migrations/19.0.1.2.0/post-migrate.py` es deliberadamente conservador:
solo hace `SELECT` contra `information_schema.columns` para verificar que
las 4 columnas nuevas quedaron creadas, y loggea una advertencia si no --
cero DDL propio, cero riesgo adicional sobre datos reales.

Se subió la versión del manifest de `19.0.1.1.0` a `19.0.1.2.0`
(`__manifest__.py.propuesto`) siguiendo semver de Odoo (tercer dígito =
cambio de funcionalidad menor, no fix de patch) -- eso es lo que dispara
que Odoo ejecute la carpeta `migrations/19.0.1.2.0/` en el próximo `-u`.

## 5. Pasos exactos para aplicar en `ionos` (a correr por el usuario, NO por mí)

Esto asume el flujo de trabajo normal del repo (es un git repo con remoto
`git@github.com-medicinedepot:MDSODOO/COMMUNITY.git`, rama `main`, 20
commits por delante de `origin/main` al momento de esta auditoría -- ese
estado del repo es preexistente a esta tarea, no algo que yo haya tocado).

```bash
# 1. Traer los .propuesto de esta carpeta al working copy local (NO en
#    ionos), aplicarlos como el contenido real de cada archivo del módulo,
#    revisar el diff con calma:
#      __manifest__.py
#      models/ai_query_log.py
#      models/image_quote_image.py
#      models/image_quote_request.py
#      services/ollama_client.py
#      services/image_quote_processor.py
#      services/inventory_nl_resolver.py
#      migrations/19.0.1.2.0/post-migrate.py   (archivo nuevo)

# 2. Commit + push normal del repo (según el flujo que ya usan --
#    ver commits previos del módulo con:
#    git log --oneline -- custom_addons/local_ai_connector)

# 3. En ionos, traer los cambios al checkout que monta el contenedor
#    (custom_addons/ está montado como bind mount, ver docker-compose.yml:
#    "./custom_addons:/mnt/extra-addons"), p.ej.:
ssh ionos "cd /opt/medicinedepot-odoo19-migration && git pull"

# 4. Actualizar SOLO este módulo (no un -u all) contra la BD dev primero:
ssh ionos "docker exec medicinedepot_dev_odoo \
  odoo -u local_ai_connector -d medicinedepot_dev --stop-after-init"

# 5. Revisar el log de esa corrida -- buscar la línea de
#    post-migrate.py ("columnas de instrumentacion de latencia ...
#    verificadas OK") y confirmar que no hubo errores de carga.

# 6. Confirmar las columnas directamente en Postgres (opcional, ya lo
#    hace el post-migrate, pero para verificar a mano):
ssh ionos "docker exec medicinedepot_dev_db psql -U odoo -d medicinedepot_dev -c \"
  SELECT column_name FROM information_schema.columns
  WHERE table_name IN ('local_ai_query_log','local_ai_image_quote_image','local_ai_image_quote_request')
  AND column_name IN ('duration_seconds','processing_started_at','processing_pid');\""

# 7. Reiniciar el contenedor de Odoo para que el proceso cargue el código
#    Python nuevo de los servicios (ollama_client.py / image_quote_processor.py
#    / inventory_nl_resolver.py no son solo XML -- son .py, así que además
#    del -u hace falta el restart, según ya está anotado en la memoria del
#    proyecto: "cambios a modelos Python necesitan docker restart, -u solo
#    no basta"):
ssh ionos "docker restart medicinedepot_dev_odoo"

# 8. Verificación funcional mínima: disparar una consulta de inventario en
#    lenguaje natural (o esperar al cron de cotización por imagen, cada 2
#    min) y confirmar que duration_seconds queda poblado con un valor > 0
#    en el registro nuevo correspondiente.
```

Nada de esto se ejecutó como parte de esta tarea -- ni el `git pull` en
`ionos`, ni el `-u`, ni el `restart`. Quedan aquí solo como referencia para
cuando el usuario decida aplicarlo.

## 6. Fuera de alcance / posibles siguientes pasos (NO implementados aquí)

- **Vistas**: los campos nuevos no se expusieron en
  `views/image_quote_views.xml` (no se pidió, y no hacía falta para el
  objetivo de "instrumentar" -- los datos ya son consultables por SQL/ORM
  sin vista). Si se quiere verlos en el backend de Odoo, es un cambio
  pequeño y de bajo riesgo aparte.
- **Duración en llamadas fallidas**: ver limitación conocida arriba
  (sección 1).
- **Dashboard/reporte de latencia (p50/p95)**: fuera del alcance de esta
  fase, que es solo instrumentación (captura del dato crudo).
- **Confirmar la hipótesis de restart/deploy** para los 2 casos huérfanos
  ya ocurridos: no es posible retroactivamente (no había
  `processing_started_at`/`processing_pid` en ese momento) -- esta
  instrumentación solo ayuda para la *próxima* vez que ocurra.
