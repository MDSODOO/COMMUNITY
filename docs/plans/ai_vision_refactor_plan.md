# Plan de Refactorización — Visión IA para Identificación de Productos (WhatsApp → Odoo)

**Versión:** 1.0
**Fecha:** 2026-07-29
**Modelo objetivo:** `qwen2.5vl:7b` (Ollama en host.docker.internal:11434)
**Módulo:** `local_ai_connector` v19.0.1.1.0

---

## 1. Objetivo

Refactorizar `local_ai_connector` para que, desde una foto de un producto (caja, frasco, blister, ampolleta, solución) enviada por un cliente vía WhatsApp, el sistema identifique automáticamente:
- **Nombre comercial** del producto
- **Principio activo** (ej. "paracetamol", "ibuprofeno")
- **Presentación** (ej. "solución 500ml", "30 tabletas", "caja con 20")
- **Cantidad solicitada** (unidades que el cliente pide)
- **Confianza** del modelo (0.0–1.0)

El resultado alimenta el mapeo contra `product.template` de Odoo y responde al staff con los campos `name`, `active_ingredient` (campo `x_studio_...` o `description`), `presentation`, y la cantidad "A la mano" calculada desde `stock.quant`.

---

## 2. System Prompt para qwen2.5vl:7b (Prompt Engineering)

### 2.1. Prompt de Visión — Identificador de Productos desde Foto

```
Eres un asistente especializado en identificar productos farmacéuticos para
MedicineDepot, una farmacia que opera sobre Odoo 19.

Recibirás una foto de un producto farmacéutico real enviada por un cliente
(no una lista de compras). Puede ser una caja, frasco, blister, ampolleta,
solución, o cualquier presentación de medicamento.

Tu tarea es extraer la siguiente información del empaque/etiqueta:

1. nombre_comercial: El nombre de marca del producto (ej. "Tempra", "Amoxicilina MK").
   Si no hay nombre de marca claro, usa el nombre del principio activo + laboratorio.
2. principio_activo: El o los principios activos (ej. "paracetamol", "amoxicilina").
3. presentacion: El formato y cantidad del contenido (ej. "solución 500ml",
   "30 tabletas", "caja con 20 cápsulas 500mg", "suspensión 60ml").
4. cantidad_solicitada: La cantidad de unidades que el cliente pide (ej. 2, 3, 5).
   Si no hay cantidad visible, devuelve null.
5. confianza: Tu nivel de confianza en la identificación, de 0.0 a 1.0.
   - 1.0: texto legible sin ambigüedad, nombre y presentación claros
   - 0.7-0.9: legible pero con algún elemento ambiguo
   - 0.4-0.6: parcialmente legible, lectura con baja certeza
   - 0.0-0.3: imagen poco clara, borrosa, o sin texto farmacéutico identificable

Consideraciones importantes:
- La foto puede tener iluminación variable, ángulos inclinados, fondos diversos
  (mesas, mostradores, manos sosteniendo el producto) -- NO dejes de intentar
  la lectura por esto.
- El texto puede estar en español o inglés.
- Si el empaque muestra código de barras, inclúyelo como referencia opcional
  pero NO como sustituto de la identificación visual.
- NO inventes información -- si no ves un dato, devuelve null para ese campo.
- Si la imagen NO es un producto farmacéutico o no contiene texto legible,
  devuelve confianza < 0.3.

Ejemplos:
- Foto de caja "PARACETAMOL 500MG C/20 TAB" -> nombre: "Paracetamol 500mg",
  principio: "paracetamol", presentacion: "caja con 20 tabletas 500mg",
  cantidad_solicitada: null, confianza: 0.95
- Foto de frasco "IBUPROFENO SUSPENSIÓN 100ml" con nota "x2" ->
  nombre: "Ibuprofeno suspensión 100ml", principio: "ibuprofeno",
  presentacion: "suspensión 100ml", cantidad_solicitada: 2, confianza: 0.9

Responde ÚNICAMENTE con el JSON solicitado, sin texto adicional.
```

### 2.2. JSON Schema (parámetro `format` de Ollama)

```json
{
  "type": "object",
  "properties": {
    "nombre_comercial": {"type": ["string", "null"]},
    "principio_activo": {"type": ["string", "null"]},
    "presentacion": {"type": ["string", "null"]},
    "cantidad_solicitada": {"type": ["integer", "null"]},
    "confianza": {"type": "number", "minimum": 0.0, "maximum": 1.0}
  },
  "required": [
    "nombre_comercial",
    "principio_activo",
    "presentacion",
    "cantidad_solicitada",
    "confianza"
  ]
}
```

### 2.3. Mapeo JSON → product.template

| Campo JSON | Campo Odoo | Notas |
|---|---|---|
| `nombre_comercial` | `product.template.name` | Se usa como búsqueda primaria |
| `principio_activo` | `product.template.x_studio_active_ingredient` o `description_sale` | Fallback a `description` |
| `presentacion` | `product.template.x_studio_presentation` o se parsea de `name` | |
| `cantidad_solicitada` | Se usa como `product_uom_qty` en la línea de `sale.order` | |
| `confianza` | Se guarda en `local.ai.vision.identification.confidence` | Trazabilidad |
| `qty_available` | `stock.quant` → **"A la mano"** | Término OBLIGATORIO |

### 2.4. Reglas de negocio para el mapeo

1. **Búsqueda por nombre_comercial**: `ilike` con `sale_ok=True`
2. **Fallback por principio_activo**: si el nombre no da match único, buscar por principio activo en `description`/`x_studio_active_ingredient`
3. **Presentación**: se extrae del JSON pero NO como filtro de búsqueda (muy variable entre clientes); se muestra como referencia al staff
4. **Confianza**:
   - `>= 0.8`: match automático sugerido como "alta confianza"
   - `>= 0.5 y < 0.8`: match sugerido, requiere revisión staff
   - `< 0.5`: no sugerir producto, mostrar raw al staff
5. **"A la mano"**: el único término en UI/backend/informes para la cantidad física. `qty_available` se transforma a "A la mano" en todas las respuestas.

---

## 3. Arquitectura de Cambios

### 3.1. Nuevos archivos

| Archivo | Propósito |
|---|---|
| `services/vision_product_identifier.py` | Nuevo servicio: llama a Ollama con el prompt de visión, parsea resultado, mapea a `product.template` |
| `services/vision_product_identifier.py` → usa `ollama_client.generate_structured()` | Reutiliza el cliente existente con circuit breaker |
| `models/vision_identification.py` | Nuevo modelo: `local.ai.vision.identification` — log de cada identificación |
| `controllers/vision_from_whatsapp.py` | Nuevo endpoint `/ai/identify_product_from_photo` (staff, `auth='user'`) |
| `static/tests/e2e/ai_vision_e2e.spec.ts` | Pruebas E2E con Playwright |

### 3.2. Archivos a modificar

| Archivo | Cambio |
|---|---|
| `services/__init__.py` | Agregar `from . import vision_product_identifier` |
| `models/__init__.py` | Agregar `from . import vision_identification` |
| `services/prompt_templates.py` | Agregar `VISION_PRODUCT_IDENTIFIER_PROMPT` y `VISION_PRODUCT_IDENTIFIER_SCHEMA` |
| `services/ollama_client.py` | Sin cambios (ya soporta imágenes, circuit breaker, advisory lock) |
| `controllers/__init__.py` | Agregar `from . import vision_from_whatsapp` |
| `__manifest__.py` | Agregar `security/ir.model.access.csv` para el nuevo modelo si aplica |

### 3.3. Flujo completo

```
Cliente WhatsApp → Foto → Staff Odoo → /ai/identify_product_from_photo
                                          │
                                          ▼
                                    ollama_client.generate_structured(
                                        model=qwen2.5vl:7b,
                                        prompt=VISION_PRODUCT_IDENTIFIER_PROMPT,
                                        json_schema=VISION_PRODUCT_IDENTIFIER_SCHEMA,
                                        images=[img_b64],
                                        timeout=VISION_TIMEOUT,
                                        num_ctx=4096,
                                        priority='low',
                                        cr=env.cr,
                                    )
                                          │
                                          ▼
                                    vision_product_identifier.py
                                    - Parsear JSON
                                    - Buscar product.template
                                    - Calcular "A la mano"
                                          │
                                          ▼
                                    Respuesta JSON:
                                    {
                                        "success": true,
                                        "product": { id, name, "A la mano": N },
                                        "identification": { nombre_comercial, ... },
                                        "confidence": 0.95
                                    }
```

---

## 4. Manejo de Errores Específico

### 4.1. "Ollama is busy" (advisory lock ocupado)

- **Causa**: otra solicitud de visión en curso
- **Acción**: `OllamaBusyError` → responder `{"success": false, "error": "busy", "message": "El modelo de IA está procesando otra imagen. Intenta de nuevo en un momento."}`
- **HTTP 503** (Service Unavailable)

### 4.2. Timeout (VISION_TIMEOUT = 300s)

- **Causa**: la imagen tarda más de 5 minutos en procesarse
- **Acción**: circuit breaker registra fallo → `OllamaError` → responder `{"success": false, "error": "timeout", "message": "La imagen tardó demasiado en procesarse. Intenta con una foto más pequeña o con mejor iluminación."}`
- **HTTP 504** (Gateway Timeout)
- Tras 5 timeouts consecutivos → degraded mode por 5 minutos

### 4.3. Conexión rechazada (Ollama caído)

- **Causa**: Ollama no está corriendo en host.docker.internal:11434
- **Acción**: `requests.ConnectionError` → responder `{"success": false, "error": "ai_unavailable", "message": "El servicio de IA local no está disponible en este momento. Contacta al administrador del sistema."}`
- **HTTP 503**

### 4.4. Circuit breaker (5+ fallos consecutivos)

- Ya implementado en `ollama_client.py` (`_is_vision_degraded()`, `CIRCUIT_BREAKER_THRESHOLD=5`, `CIRCUIT_BREAKER_RESET_TIMEOUT=300`)
- Rechaza automáticamente con `OllamaBusyError` durante 5 minutos
- No requiere cambios en el nuevo código — reutiliza el breaker existente

### 4.5. Advisory Lock (concurrencia)

- `_acquire_ollama_lock(cr, timeout=300.0)` ya implementado
- Adquiere un `pg_try_advisory_lock()` antes de cada inferencia de visión
- Si no lo obtiene en 300s → `OllamaBusyError`

---

## 5. Integración con WhatsApp (Staff-side)

El flujo actual de WhatsApp es:

1. Cliente envía foto por WhatsApp a un número del staff
2. Staff descarga la foto y la sube manualmente a Odoo (vía el diálogo existente "Nueva cotización desde imagen" o el nuevo endpoint de identificación)

**No hay API de WhatsApp en este proyecto** — confirmado en `docs/AI_MODEL_ODOO_CONFIG.md §9.1`. La integración es mediante enlaces `wa.me/...` (click-to-chat). El staff opera como intermediario humano entre WhatsApp y Odoo.

El nuevo endpoint `/ai/identify_product_from_photo` se integra en:
- El diálogo del Command Palette (staff selecciona "Identificar producto desde foto")
- O un botón/badge en la vista de `product.template` que abre un uploader puntual

---

## 6. Implementación Paso a Paso

### Fase 1: Prompt + Servicio (1 día)

1. Agregar `VISION_PRODUCT_IDENTIFIER_PROMPT` y `VISION_PRODUCT_IDENTIFIER_SCHEMA` a `services/prompt_templates.py`
2. Crear `services/vision_product_identifier.py` con:
   - `identify_product_from_photo(env, image_b64) → dict`
   - Llama a `ollama_client.generate_structured()` con el prompt de visión
   - Parsear la respuesta y buscar en `product.template`
   - Calcular "A la mano" desde `stock.quant`
   - Loggear en `local.ai.vision.identification`

### Fase 2: Controlador (0.5 día)

3. Crear `controllers/vision_from_whatsapp.py` con:
   - Ruta `/ai/identify_product_from_photo` (POST, `auth='user'`)
   - Rate limit: 20 solicitudes/hora por usuario (más generoso que el público porque es staff)
   - Validación: JPEG/PNG, máximo 8MB
   - Llama a `vision_product_identifier.identify_product_from_photo()`
   - Maneja errores según §4

### Fase 3: Modelo de log (0.5 día)

4. Crear `models/vision_identification.py`:
   - `local.ai.vision.identification`
   - Campos: `user_id`, `image_filename`, `raw_model_output` (text), `product_id`, `confidence`, `nombre_comercial`, `principio_activo`, `presentacion`, `on_hand` (Float), `success` (Boolean), `error_message`

### Fase 4: Pruebas E2E (1 día)

5. Crear `static/tests/e2e/ai_vision_e2e.spec.ts` (Playwright)
6. Crear fixture de imagen de prueba (caja de producto sintética)
7. Probar casos: éxito, producto no encontrado, Ollama ocupado (circuit breaker), timeout

### Fase 5: Integración UI (0.5 día)

8. Agregar entrada en el Command Palette (`md_command_palette`): "Identificar producto desde foto"
9. Mostrar resultado en un diálogo/drawer con los campos mapeados

---

## 7. Seguridad y Gobernanza

- **`sudo()`**: el nuevo controlador usa `auth='user'`, por lo que tiene sesión de staff. Los accesos a `product.template` y `stock.quant` se hacen con `sudo()` porque el staff autenticado ya tiene permisos vía ACLs de Odoo (mismo patrón que `ai_api.py`).
- **Rate limit**: DB-backed (mismo patrón que `local.ai.image.quote.attempt`), contado por `user_id`.
- **CSRF**: el endpoint staff usa `type='http'` con `csrf=True` porque `auth='user'` tiene sesión Odoo real, no necesitamos `csrf=False`.
- **Auditoría**: cada identificación queda registrada en `local.ai.vision.identification`.
- **Término "A la mano"**: toda respuesta al staff sobre cantidad física usa exclusivamente "A la mano". Los logs internos pueden almacenar `on_hand` como nombre de campo Python, pero cualquier display/mensaje lo transforma.

---

## 8. Puertas de Salida / Rollback

1. Si `qwen2.5vl:7b` falla sistemáticamente en producto fotografiado (no listas escritas), se puede:
   - Degradar a solo mostrar el raw del modelo al staff sin matching automático
   - Evaluar `llava:7b` o `moondream:1.8b` como alternativa ligera (aunque moondream ya fue descartado para texto impreso)
   - Evaluar OCR serverless (Google Vision, AWS Textract) como respaldo externo
2. Si la latencia es demasiado alta para el flujo staff:
   - Procesar en cola asíncrona (reutilizar el cron existente de `image_quote_processor.py`)
   - El staff recibe notificación cuando la identificación esté lista
