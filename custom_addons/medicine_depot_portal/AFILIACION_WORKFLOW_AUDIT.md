# AFILIACION_WORKFLOW_AUDIT

## a) Resumen del Flujo

1. El usuario abre `GET /afiliacion`.
2. El método `afiliacion()` en `medicine_depot_portal/controllers/portal.py` (ruta `@route(['/afiliacion'], type='http', auth='public', website=True, methods=['GET', 'POST'])`) renderiza `medicine_depot_portal.afiliacion_page`.
3. El QWeb `views/afiliacion_templates.xml` muestra formulario multipart (`id="afiliacion_form"`) con `csrf_token`, datos generales, selecciones Studio y carga de documentos.
4. En frontend, `static/src/js/afiliacion.js` intercepta submit y envía `fetch("/afiliacion", { method: "POST", body: new FormData(form) })`.
5. En `POST /afiliacion`, backend:
   - Si el usuario autenticado ya está afiliado (`x_studio_contact_type == 'cliente'`), devuelve JSON error.
   - Construye `partner_vals` desde inputs (`nombre`, `email`, `telefono`, `especialidad`, y campos Studio).
   - Lee archivos desde `request.httprequest.files`, los codifica Base64 y los asigna a binarios Studio.
   - Resuelve target de escritura: `partner` logueado, o búsqueda por `email`, o creación de `res.partner` nuevo.
   - Ejecuta `write()` o `create()` con `sudo()`.
6. Respuesta esperada para frontend: `{"success": true}`. El JS muestra pantalla de éxito; si falla, reactiva botón sin detalle de error.

## b) Mapeo de Datos (HTML -> Backend -> res.partner)

| Input HTML (`name`) | Tipo | Backend (controlador) | Campo destino `res.partner` |
|---|---|---|---|
| `nombre` | text | `_clean('nombre')` + `_assign_if_exists` | `name` |
| `email` | email | `_clean('email')` + `_assign_if_exists` | `email` |
| `telefono` | tel | `_clean('telefono')` + `_assign_if_exists` | `phone` |
| `especialidad` | text | `_clean('especialidad')` + `_assign_if_exists` | `function` |
| `x_studio_contact_type` | select | loop campos Studio | `x_studio_contact_type` |
| `x_studio_person_type` | select | loop campos Studio | `x_studio_person_type` |
| `x_studio_branch_office` | select | loop campos Studio | `x_studio_branch_office` |
| `x_studio_operation_notice` | file | `_get_portal_account_upload_vals()` | `x_studio_operation_notice` (+ `_filename` si existe) |
| `x_studio_sanitary_license` | file | `_get_portal_account_upload_vals()` | `x_studio_sanitary_license` (+ `_filename`) |
| `x_studio_sanitary_responsible_notice` | file | `_get_portal_account_upload_vals()` | `x_studio_sanitary_responsible_notice` (+ `_filename`) |
| `x_studio_ine` | file | `_get_portal_account_upload_vals()` | `x_studio_ine` (+ `_filename`) |
| `x_studio_proof_of_address` | file | `_get_portal_account_upload_vals()` | `x_studio_proof_of_address` (+ `_filename`) |
| `x_studio_professional_license` | file | `_get_portal_account_upload_vals()` | `x_studio_professional_license` (+ `_filename`) |
| `x_studio_tax_status_certificate` | file | `_get_portal_account_upload_vals()` | `x_studio_tax_status_certificate` (+ `_filename`) |
| `privacy` | checkbox | No se procesa en backend | Sin persistencia |
| `csrf_token` | hidden | Validación CSRF framework Odoo (`type='http'`) | No persistencia |

Notas técnicas:
- `accept=".pdf,.jpg,.jpeg,.png"` solo restringe UI navegador.
- Prueba existente (`tests/test_afiliacion_template.py`) confirma que backend acepta `text/plain` en upload (ejemplo `.txt`).

## b.1) Flujo de Carga del Usuario y Reflejo en el Sistema

1. El usuario entra a `/afiliacion` y ve el formulario precargado si está logueado (`partner` en qcontext).
2. Captura datos generales y selecciona opciones Studio.
3. Adjunta archivos COFEPRIS/legales; el navegador los mantiene en memoria hasta enviar.
4. Al enviar, `afiliacion.js` arma `FormData(form)` con todos los campos (texto + binarios + `csrf_token`) y hace `POST /afiliacion`.
5. En servidor, `afiliacion()` procesa:
   - Normaliza strings (`strip`) para datos generales.
   - Extrae binarios de `request.httprequest.files`.
   - Convierte cada archivo a Base64 y lo coloca en los campos binarios Studio de `res.partner`.
6. Persistencia en Odoo:
   - Si hay partner objetivo, se ejecuta `partner.write(partner_vals)`.
   - Si no existe partner objetivo, se ejecuta `res.partner.create(partner_vals)`.
7. Reflejo funcional inmediato:
   - En backend, el contacto queda actualizado/creado en **Contactos** (`res.partner`) con nombre, correo, teléfono, especialidad y selecciones Studio.
   - Los documentos quedan guardados en campos binarios del partner (`x_studio_*`) y, si existe el campo técnico, también se guarda `*_filename`.
8. Reflejo en portal web:
   - Si el usuario vuelve a `/afiliacion`, los campos de texto aparecen con `t-att-value` desde `partner`.
   - En inputs file no se repuebla el archivo por seguridad del navegador, pero aparece el texto “Documento cargado actualmente.” cuando el binario ya existe.
   - En `/my/account` y estado de afiliación, el sistema calcula faltantes con `_get_affiliation_state()` y muestra alertas de documentos pendientes.

## c) Vulnerabilidades o Puntos de Falla

> **Nota de revisión (2026-07-27, Data Migration Architect):** este documento y el código
> de `portal.py` quedaron congelados en el mismo commit baseline (`9ca60a9`, 2026-07-24),
> pero el código ya incluía correcciones que este documento no reflejaba. Se verificó
> línea por línea contra el código real antes de tocar nada más. Estado actualizado abajo.

### Ya corregidos en el código actual (verificado 2026-07-27)

1. ~~**Ruta pública con escritura `sudo()` sobre `res.partner` por email**~~ — **CORREGIDO.**
   Si el email ya existe y quien envía es un usuario público, el backend devuelve `409`
   ("Ya existe una cuenta con ese correo...") y **nunca** ejecuta `write()` sobre ese
   partner. Un usuario público solo puede llegar a `create()` de un partner nuevo, jamás
   a modificar uno existente sin autenticación.

2. ~~**Carga de archivos sin validación de tipo MIME/extensión/tamaño**~~ — **CORREGIDO.**
   `_build_upload_vals` valida extensión (`_AFFILIATION_ALLOWED_EXTENSIONS`), MIME
   (`_AFFILIATION_ALLOWED_MIME_TYPES`) y tamaño máximo (5 MB,
   `_AFFILIATION_MAX_FILE_SIZE_BYTES`).

3. ~~**Validación de campos obligatorios depende casi totalmente del cliente**~~ — **CORREGIDO.**
   `_validate_affiliation_post` valida `nombre`, `email` (formato incluido), `telefono`,
   `especialidad` y `privacy` en el backend antes de procesar.

4. ~~**Manejo de error opaco en frontend**~~ — **CORREGIDO.** `afiliacion.js` (`_onSubmit`)
   lee `data.payload.message` del backend y lo muestra vía `_showError()`; solo cae a un
   mensaje genérico si la respuesta no trae JSON válido.

5. ~~**Sin control antifraude/antibot**~~ — **CORREGIDO (2026-07-28).** Rate limit de 5
   intentos / 15 min por IP, respaldado en Postgres (modelo
   `medicine.depot.affiliation.attempt`) en vez de un contador en memoria — necesario
   porque `config/odoo.conf` corre con `workers = 5` y un contador in-process no vería
   los intentos que caen en otros workers. Excedido el límite, el endpoint responde `429`
   sin tocar el modelo de negocio. No cubre reCAPTCHA/challenge, solo throttling por IP.

### Sigue abierto (verificado 2026-07-27, actualizado 2026-07-28)

### Medio

6. **`privacy` no auditado** — **parcialmente corregido (2026-07-28).** Cada aceptación de
   `/afiliacion` ahora deja evidencia en el log del servidor (`partner_id`, `email`, IP,
   User-Agent). Sigue sin persistir en un modelo dedicado con timestamp/versión del aviso
   consultable desde la UI — ver `docs/OLLAMA_MIGRATION_PLAN.md` §9 para el follow-up.

## d) Recomendaciones de Optimización

1. Cambiar flujo de escritura para usuarios no autenticados:
   - Opción A: `auth='user'` para actualización directa de `res.partner`.
   - Opción B: para público, crear lead/solicitud intermedia (`crm.lead` o modelo staging) sin tocar `res.partner` final.

2. Eliminar actualización por email en ruta pública:
   - No hacer `search(email)` en anónimo.
   - Vincular actualización solo al `partner_id` del usuario autenticado.

3. Endurecer validación backend:
   - Verificar requeridos (`nombre`, `email`, `telefono`, `especialidad`, `privacy`).
   - Validar formato de email/teléfono.
   - Responder JSON con errores por campo y status HTTP coherente.

4. Blindar uploads:
   - Limitar tamaño por archivo y total request.
   - Validar MIME real + extensión permitida.
   - Renombrar sanitizado y registrar hash.
   - Integrar escaneo antivirus antes de persistir.

5. Añadir controles anti-abuso:
   - reCAPTCHA/hCaptcha.
   - Rate limit por IP/sesión/email.
   - Registro de intentos fallidos.

6. Mejorar trazabilidad/auditoría:
   - Persistir consentimiento (`privacy`) con fecha/hora UTC, IP, user-agent, versión de aviso.
   - Registrar eventos de afiliación (creación, actualización, upload) en modelo de log.

7. Mejorar UX de errores:
   - En JS, mostrar mensajes del backend en un contenedor visible.
   - Diferenciar error de validación vs error interno.

## Referencias de Código Auditadas

- `medicine_depot_portal/controllers/portal.py`:
  - Ruta y flujo GET/POST `/afiliacion`.
  - `_get_portal_account_upload_vals` para archivos.
  - `_prepare_afiliacion_qcontext` y opciones de selección.
- `medicine_depot_portal/views/afiliacion_templates.xml`:
  - Formulario, CSRF, inputs, selects, files, checkbox `privacy`.
- `medicine_depot_portal/static/src/js/afiliacion.js`:
  - Submit AJAX, manejo de éxito/error.
- `medicine_depot_portal/tests/test_afiliacion_template.py`:
  - Smoke test multipart con archivos `text/plain`.
