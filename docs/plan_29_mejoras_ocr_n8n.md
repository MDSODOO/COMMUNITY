# Plan Táctico: OCR + Optimización de Workflows n8n — Medicine Depot

**Fecha:** 2026-08-10
**Autor:** Arquitectura de IA / Automatización (auditoría asistida)
**Alcance:** 29 mejoras concretas sobre el stack `md_n8n` (servidor Ionos) e integración con Odoo 19 (`medicinedepot_dev`)

## Hallazgos de la auditoría (base de este plan)

- Contenedor `md_n8n` corre sobre **Docker Hardened Images (Alpine 3.24)**: sin `apk`, sin `tesseract`, `convert`, `gs` ni `python3` disponibles dentro del contenedor. No se puede instalar OCR local directamente en la imagen de n8n.
- Host Ionos: 8 vCPU, 15.5 GiB RAM (11 GiB disponibles), 419 GB disco libre → capacidad de sobra para un contenedor sidecar de OCR local.
- n8n `2.33.7`, sin community nodes instalados.
- Los 5 workflows existentes (`01_healthcheck_odoo`, `02_conciliacion_inventario`, `03_alertas_lotes_vencimiento`, `04_sync_ordenes_compra`, `05_reporte_ventas_diario`) **no tienen `errorWorkflow` configurado, ni `retryOnFail` ni `onError` en ningún nodo** — cero tolerancia a fallos en todo el stack.
- **`01`, `02`, `03` y `05` están `active: false`** — es decir, healthcheck de Odoo, conciliación de inventario, alertas de caducidad y reporte de ventas diario actualmente **no se ejecutan**.
- Todas las llamadas a Odoo se hacen con nodos `httpRequest` genéricos contra XML-RPC (no el nodo nativo de Odoo, sin pooling ni reintentos).
- `04_sync_ordenes_compra` tiene 23 nodos y es el workflow más complejo del stack, pero comparte el mismo vacío de manejo de errores que el resto.
- Red Docker `medicinedepot_dev_default` ya conecta `md_n8n`, `md_n8n_db`, `medicinedepot_dev_odoo`, `medicinedepot_dev_db` y `md_caddy` — un sidecar OCR unido a esa red es alcanzable internamente sin exponer puertos públicos.

## Decisión de arquitectura OCR

**Híbrida, local-primero:** contenedor sidecar con Tesseract/PaddleOCR (dato médico/farmacéutico se queda on-premise, sin costo por página) como extracción primaria, con **escalamiento condicional** a una API cloud (Google Document AI o AWS Textract) solo cuando la confianza del OCR local cae bajo un umbral. Esto minimiza costo recurrente y exposición de datos sensibles, reservando el fallback cloud para los documentos realmente difíciles (manuscritos, escaneos de baja calidad).

---

## a) Implementación y Precisión del OCR (8)

1. Desplegar un contenedor sidecar `md_ocr_service` (imagen basada en `tesseract-ocr` + wrapper FastAPI) unido a la red `medicinedepot_dev_default`, expuesto solo internamente como `http://ocr-service:8000`.
2. Configurar Tesseract con el paquete de idioma `spa` (español) como primario, dado que las facturas/órdenes de proveedores locales están en español.
3. Añadir preprocesamiento de imagen (deskew, binarización adaptativa, aumento de DPI a 300) antes de OCR para elevar precisión en escaneos de baja calidad de proveedores.
4. Implementar extracción de campos estructurados vía plantillas regex/posicionales por tipo de documento (factura de proveedor, orden de compra, remisión) en vez de texto plano sin estructurar.
5. Definir un umbral de confianza (`confidence_threshold = 80`) por campo extraído; campos bajo el umbral se marcan `requires_review: true` en vez de pasar directo a Odoo.
6. Implementar el fallback condicional a Google Document AI/AWS Textract **solo** para documentos con confianza global de Tesseract por debajo de 60%, para controlar costo por llamada.
7. Añadir soporte para extracción de tablas (líneas de producto/cantidad/precio) usando `pytesseract` con detección de bounding boxes en vez de solo texto lineal, crítico para reconstruir líneas de orden de compra.
8. Construir un dataset de validación con 20-30 facturas/órdenes reales históricas de proveedores de Medicine Depot para medir precisión (accuracy por campo) antes de activar el flujo en producción.

## b) Optimización de nodos y consumo de memoria en workflows actuales (7)

9. **Reactivar `01_healthcheck_odoo`, `02_conciliacion_inventario`, `03_alertas_lotes_vencimiento` y `05_reporte_ventas_diario`** — están inactivos desde su creación; sin ellos no hay monitoreo real de salud de Odoo ni alertas de caducidad corriendo.
10. Sustituir los nodos `httpRequest` que llaman a Odoo XML-RPC por el nodo nativo `n8n-nodes-base.odoo` (o un nodo HTTP con conexión reutilizable) para aprovechar pooling de conexión y reducir overhead por ejecución.
11. Revisar los nodos `Code` de `02`, `03` y `05` para mover lógica de transformación pesada (parsing de listas grandes) a Function nodes con streaming/batch en vez de cargar el dataset completo en memoria de una sola pasada.
12. Configurar `EXECUTIONS_DATA_MAX_AGE` (actualmente 720h) junto con `EXECUTIONS_DATA_PRUNE_MAX_COUNT` para acotar también por número de ejecuciones, no solo por antigüedad, evitando crecimiento descontrolado de la BD de n8n bajo el nuevo volumen de ejecuciones OCR.
13. En `04_sync_ordenes_compra` (23 nodos), consolidar los nodos `Code` consecutivos que solo transforman campos sin lógica condicional en un único nodo, reduciendo la sobrecarga de serialización entre nodos.
14. Añadir `alwaysOutputData: false` explícito en nodos de consulta (`httpRequest` hacia Odoo) donde no se necesita el payload completo aguas abajo, reduciendo memoria retenida por ejecución.
15. Habilitar el modo de ejecución en cola (`EXECUTIONS_MODE=queue` con Redis) si el volumen de documentos OCR proyectado supera ~50/día, para no bloquear el proceso principal de n8n con extracciones largas.

## c) Tolerancia a fallos y manejo de errores (7)

16. Crear un **workflow de error compartido** (`00_error_handler_global.json`) con un nodo `Error Trigger` que capture nombre de workflow, nodo fallido y mensaje, y lo enrute a un tema de Telegram dedicado (ej. reutilizando el patrón de Forum Topics ya implementado en `04`).
17. Configurar `settings.errorWorkflow` en los 5 workflows existentes (actualmente ninguno lo tiene) apuntando al workflow del punto 16.
18. Añadir `retryOnFail: true` con `maxTries: 3` y `waitBetweenTries` en todos los nodos `httpRequest` que llaman a Odoo, dado que XML-RPC puede fallar por timeouts transitorios de carga.
19. En el nuevo flujo OCR, envolver la llamada al sidecar `ocr-service` y al fallback cloud en nodos con `onError: "continueErrorOutput"`, para que un documento ilegible no tumbe la ejecución completa sino que se enrute a revisión manual.
20. Implementar un nodo `IF` de circuito-breaker simple: si el sidecar OCR local falla 3 veces consecutivas (estado guardado en `n8n_db` o vía `staticData`), pausar el enrutamiento a OCR local y notificar a Telegram en vez de reintentar indefinidamente.
21. Añadir validación de esquema (JSON Schema o nodo `Code` con checks explícitos) al payload del webhook `sync-purchase-order` y del nuevo `ocr-process-document`, rechazando con 400 claro en vez de fallar más adelante en un nodo de Odoo.
22. Instrumentar todos los workflows con un nodo final de log estructurado (éxito/fallo/duración) hacia una tabla Postgres de auditoría, para poder diagnosticar fallos intermitentes sin depender solo del panel de ejecuciones de n8n.

## d) Integración del JSON extraído hacia Odoo 19 (XML-RPC/REST) (7)

23. Definir el contrato JSON normalizado de salida del OCR (`invoice_number`, `vendor_vat`, `date`, `lines[]{product_code, qty, unit_price}`, `confidence_by_field`) como esquema único consumido por todos los nodos downstream, siguiendo el mismo patrón de "Preparar Post-Creacion" ya usado en `04`.
24. Mapear `vendor_vat` extraído contra `res.partner` en Odoo vía XML-RPC `search_read` con normalización de formato (espacios, guiones) antes de intentar un match exacto, ya que el OCR puede introducir variaciones menores.
25. Crear el borrador de factura de proveedor (`account.move`, `move_type: in_invoice`) en estado `draft` cuando la confianza sea alta, y en `draft` con una nota/actividad de "revisión requerida" asignada a un usuario cuando algún campo esté bajo el umbral de confianza (punto 5).
26. Adjuntar el documento original (imagen/PDF fuente) al registro de Odoo creado vía `ir.attachment` (XML-RPC `create` con `res_model`/`res_id`), preservando trazabilidad entre el documento físico y el asiento generado.
27. Reutilizar el nodo "Validar Payload" y el patrón de enrutamiento por `message_thread_id` ya implementado en `04_sync_ordenes_compra` para notificar el resultado del OCR al tema de Telegram correspondiente (Compras, o uno nuevo "OCR / Revisión Manual" si el volumen lo justifica).
28. Implementar reconciliación de líneas de producto: hacer `search_read` contra `product.product` por código de barras/referencia interna extraída por OCR, con fallback a búsqueda difusa por nombre cuando no haya match exacto, antes de construir las líneas de `account.move.line`.
29. Añadir un endpoint de confirmación humana (`n8n-nodes-base.webhook` adicional, ej. `ocr-confirm-review`) que permita a un usuario aprobar/corregir campos marcados `requires_review` y dispare la creación final en Odoo, cerrando el ciclo humano-en-el-loop para documentos de baja confianza.

---

## Siguientes pasos sugeridos (fuera del conteo de 29, solo referencia)

- Validar con el usuario si se autoriza credencial de Google Document AI/AWS Textract antes de implementar el punto 6 (fallback cloud), dado que implica costo recurrente y salida de datos del entorno on-premise.
- Priorizar el punto 9 (reactivar workflows inactivos) y el bloque de tolerancia a fallos (16-22) antes de sumar carga OCR nueva al stack.
