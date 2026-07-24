# Changelog — purchase_invoice_parser

Historial generado automáticamente a partir de `git log -- purchase_invoice_parser`. No es prosa editorial: cada línea es un commit real. Mantener actualizado: después de modificar este módulo, anteponer la entrada nueva bajo la fecha de hoy (o crear el día si no existe).

**Commits registrados:** 135 | **Rango:** 2026-04-28 → 2026-06-30

---

## 2026-07-03

- 🔍 (sin commit aún) fix(purchase_invoice_parser): code-review (alto esfuerzo, 8 ángulos) de los Hard Stops de IVA/Lote agregados el mismo día. Hallazgo principal (confirmado independientemente por 5 de 8 ángulos): `_validate_line_iva` comparaba la tasa del CFDI contra `product.supplier_taxes_id` **sin acotar por compañía**, a diferencia de `TaxResolver` que sí hace `with_company()` + fallback cross-company — riesgo real de reintroducir, en otra forma, la misma clase de falso bloqueo que motivó revertir un `UserError` similar en `c84e84f` (ej. producto con impuesto configurado para Matriz bloqueando un CFDI legítimo de una sucursal con tasa distinta, como Chetumal 8% Compras Sur). Corregido: `_validate_before_create`/`_validate_line_iva` ahora reciben `target_company` y filtran `supplier_taxes_id` por `company_id in (False, target_company.id)`, igual criterio que `TaxResolver`. Además: se agregó el método compartido `PurchaseInvoiceImportWizardLine._valid_lots()` para eliminar la duplicación de `line.lot_ids.filtered(lambda l: l.name)` entre la validación y `purchase_order_builder.py`; se reescribieron los docstrings de `_validate_before_create`/`_validate_line_iva`/`_validate_line_lot` a formato Google (Args/Returns) por la regla del CLAUDE.md raíz; se simplificaron firmas (ya no se pasa `product` como parámetro redundante). No corregido (fuera de alcance, notado para seguimiento aparte): el E2E `tests/playwright/e2e_purchase_xml_import.spec.js` podría fallar si los fixtures de staging disparan alguno de los dos Hard Stops — pendiente de verificar contra datos reales.
- 🔒 (sin commit aún) feat(purchase_invoice_parser): Hard Stops de validación antes de crear la Orden de Compra — bloquea (`ValidationError`) cuando (1) el CFDI trae una tasa de IVA distinta de cero que no coincide con ninguna tasa configurada en `supplier_taxes_id` del producto (excepción intencional: CFDI 0%/Exento siempre se permite, aunque el producto tenga configurada una tasa distinta — decisión explícita para no repetir la fricción del bloqueo por IVA revertido en `c84e84f`), o (2) el producto tiene `tracking == 'lot'` y ninguna línea trae un lote válido extraído del XML/PDF ("A la Mano" / On Hand). Nuevos métodos `_validate_before_create`, `_validate_line_iva`, `_validate_line_lot` en `purchase_invoice_import_wizard.py`, llamados desde `action_create_purchase_order`. Tests nuevos en `tests/test_invoice_parser.py` (`test_block_invalid_iva`, `test_allows_exento_cfdi_even_if_product_has_configured_tax`, `test_block_missing_lot`). Se ajustaron 6 tests preexistentes en `tests/test_purchase_invoice_import_wizard.py` que usaban productos con `tracking='lot'` sin lotes para agregarles un lote de fixture y no chocar con el nuevo Hard Stop. Hallazgo colateral (no corregido, fuera de alcance): `test_create_po_raises_when_iva_not_found_for_matriz` ya estaba roto desde `c84e84f` (espera un `UserError` con texto "Matriz" que ningún código actual produce).
- ✨ (sin commit aún) style(purchase_invoice_parser): completar la migración Bento del wizard "Importar XML de Proveedor" — auditoría UI con Playwright (`e2e_tests/audit_wizard_ui.spec.ts`) detectó que el `modal-content` nativo de Odoo (4px de radio) y el PASO 2 completo (grupos "Datos del CFDI"/"Proveedor" y tabla de conceptos) seguían sin el tratamiento Bento que ya tenía el PASO 1. Cambios: `border-radius: 16px` + sombra suave en el modal (escopado con `:has(.pip_bento_card)` para no afectar otros diálogos de Odoo), botón "Cancelar" ahora pill (999px) para igualar al primario, grupos del PASO 2 envueltos en `.pip_bento_grid--review`/`.pip_bento_card--compact`, tabla de conceptos envuelta en `.pip_bento_card--table`. Dark mode: tokens equivalentes en `backend_dark.scss` (mismo patrón de bundle `web.assets_web_dark` ya corregido el 2026-07-01).

## 2026-07-01

- ✨ (sin commit aún) style(purchase_invoice_parser): glassmorphism en las cards Bento del wizard de importación CFDI (`cfdi_upload_zone.scss`) — fondo translúcido + `backdrop-filter: blur()` con fallback opaco, en modo claro y oscuro.
- 🐛 (sin commit aún) fix(purchase_invoice_parser): mover overrides de dark mode de `cfdi_upload_zone.scss` y `price_notification_menu.scss` a nuevo `backend_dark.scss` (bundle `web.assets_web_dark`) — el selector `html[data-bs-theme="dark"]` nunca coincidía con el DOM real de Odoo 19, dejando el wizard "Importar XML" con fondo claro permanente en modo oscuro. Ver `docs/audits/2026-07-01_backend_dark_mode_audit.md`.

## 2026-06-30

- ✨ `a231291` feat(purchase_invoice_parser): zona de carga Bento con Drag & Drop (OWL)

## 2026-06-29

- 🔧 `af60e60` chore(repo): limpieza jerárquica y reorganización de archivos raíz
- 🔧 `cd4db72` chore(e2e/cfdi): agregar spec de inspección visual y outputs de auditoría de bills CFDI
- 🐛 `25f7676` fix(purchase_invoice_parser): fallback multi-empresa en TaxResolver y corrección de tax_ids para líneas exentas

## 2026-06-23

- 🐛 `a55f5cf` fix(purchase_invoice_parser): implementar regex estricta y date parser robusto para extraccion de lotes con formato quifamesa

## 2026-06-22

- 🐛 `748a07e` fix(purchase_invoice_parser): agregar atributos title a iconos fontawesome para resolver warnings de accesibilidad a11y en formularios
- 🐛 `1deb1af` fix(purchase_invoice_parser): archivar notificaciones en lugar de eliminarlas para preservar historial

## 2026-06-18

- 🐛 `d6ecc85` fix(purchase_invoice_parser): eliminar campo numbercall del cron — removido en Odoo 17+
- ✨ `6545376` feat(purchase_invoice_parser): implementar campo active para archivar registros y cron job para eliminar notificaciones historicas vencidas

## 2026-06-16

- ✨ `91c236b` feat(purchase_invoice_parser): columnas dinamicas por sucursal en Excel de Cambios de Precio
- ✨ `c0da65e` feat(purchase_invoice_parser): filtrar por Linea (x_line) en ambos wizards de reporte
- ✨ `779910a` feat(purchase_invoice_parser): corregir PDF y agregar Excel al reporte Costos por Sucursal
- ✨ `7c27598` feat(purchase_invoice_parser): reemplazar Precio Nuevo por Precio Actual en reporte PDF
- ✨ `35291e7` feat(purchase_invoice_parser): disparar notificacion de precio al confirmar OC en lugar de al crearla
- ✨ `58aa117` feat(purchase_invoice_parser): agregar columna Sucursal y Precio Actual al Excel de cambios de precio
- 🐛 `4036cce` fix(purchase_invoice_parser): colapsar espacio en blanco en header de reporte PDF y solucionar crash en generacion de exportacion Excel
- ✨ `53351db` feat(purchase_invoice_parser): exportar notificaciones de precio a Excel y corregir espacio blanco del reporte PDF
- 🐛 `bddf19f` fix(purchase_invoice_parser): eliminar web.external_layout del reporte de precios
- 🐛 `8fcb829` fix(purchase_invoice_parser): precisar XPath para suprimir SOLO el div exterior del header striped
- 🐛 `32af629` fix(purchase_invoice_parser): corregir XPath para suprimir header striped
- 🐛 `76c2194` fix(purchase_invoice_parser): suprimir header striped via xpath directo sobre t-attf-class
- 🐛 `8167061` fix(purchase_invoice_parser): remover encabezado duplicado en reporte PDF y colapsar margen superior vacio
- 🐛 `03dbd29` fix(purchase_invoice_parser): reemplazar atributo name inexistente por el campo real del modelo x_line tras auditoria de base de datos
- 🐛 `f3c02e6` fix(purchase_invoice_parser): detectar campo x_line via _fields en lugar de adivinar nombre
- 🐛 `91d5650` fix(purchase_invoice_parser): resolver laboratorio via SQL directo en lugar de ORM Studio
- 🐛 `01b9e0d` fix(purchase_invoice_parser): purgar referencia erronea x_studio_linea_id y forzar uso de categ_id nativo en reporte QWeb
- 🐛 `ae77ded` fix(purchase_invoice_parser): recuperar línea (laboratorio) con fallback seguro a categoría
- 🐛 `b63d471` fix(purchase_invoice_parser): remover dependencia de campo studio inexistente y usar categ_id nativo para el filtro de lineas
- 🐛 `b0c6c44` fix(purchase_invoice_parser): simplificar acceso a campo laboratorio en QWeb
- 🐛 `76f4777` fix(purchase_invoice_parser): usar laboratorio/línea Studio en columna LÍNEA
- 🐛 `2266f13` fix(purchase_invoice_parser): separar información PRODUCTO y LÍNEA en reporte
- 🐛 `cf712f5` fix(purchase_invoice_parser): eliminar código de barras de columna LÍNEA
- 🐛 `aeba319` fix(purchase_invoice_parser): corregir columna LÍNEA - mostrar nombre simplificado del producto
- 🐛 `a1d72ef` fix(purchase_invoice_parser): extraer campo "Línea" del modelo Studio x_line
- ✨ `abcef8f` feat(purchase_invoice_parser): replicar funcionalidad de "Costo por Sucursal" en reporte de cambios de precio
- 🐛 `0d8f264` fix(purchase_invoice_parser): corregir elemento <group> no soportado en Odoo 19 de vista search de notificaciones
- ✨ `185031e` feat(purchase_invoice_parser): expandir reporte de precios con codigo de barras, filtros por linea y comparativa de ultimo costo por sucursal
- 🐛 `d92dfc7` fix(purchase_invoice_parser): reconstruir vista search de notificaciones bajo estandares estrictos de Odoo 19
- 🐛 `4ed84b0` fix(purchase_invoice_parser): corregir renderizado HTML en chatter y mejorar formato del mensaje de cambio de precio
- ✨ `62eb263` feat(purchase_invoice_parser): implementar tests E2E con playwright y sistema de capacitacion continua (onboarding) para usuarios
- 🐛 `6727fef` fix(purchase_invoice_parser): fijar 'o' antes de external_layout en reporte
- 🐛 `476f485` fix(purchase_invoice_parser): corregir render del reporte PDF de cambios de precio
- 🔄 `e9a647d` refactor(purchase_invoice_parser): auditar modulo y estandarizar diseño de reporte PDF basandose en Pharma_reports
- 🐛 `39d6de0` fix(purchase_invoice_parser): hacer opcionales los parametros de los metodos de notificacion para compatibilidad con botones type=object
- 🐛 `9a68743` fix(purchase_invoice_parser): corregir error de external ID reordenando la carga de xml en el manifest para resolver referencias de menus
- 🐛 `4c245f1` fix(purchase_invoice_parser): quitar expand y string del group de la vista search para Odoo 19

## 2026-06-15

- 🐛 `cfbfab8` fix(purchase_invoice_parser): eliminar atributo icon invalido en menuitem para Odoo 19
- 🐛 `213a4fe` fix(purchase_invoice_parser): auditoria profunda y reconstruccion minimalista de vista search v19
- 🐛 `7feaf6d` fix(purchase_invoice_parser): reconstruir vista search de notificaciones con sintaxis estricta para Odoo 19
- 🐛 `1b21664` fix(purchase_invoice_parser): corregir sintaxis invalida en la vista search de notificaciones para Odoo 19
- 🐛 `2074d0a` fix(purchase_invoice_parser): migrar etiqueta tree a list en las vistas para resolver incompatibilidad con Odoo 19
- ✨ `00796aa` feat(purchase_invoice_parser): dashboard analítico completo para notificaciones de precio
- 🐛 `543f6f5` fix(purchase_invoice_parser): aplicar sudo() en busqueda de compañias para evitar bloqueos por ir.rule multicompania en usuarios estandar
- 🐛 `a80c09b` fix(purchase_invoice_parser): permitir acceso a notificaciones para usuarios de compras
- 🐛 `cff3223` fix(purchase_invoice_parser): grant XML upload and parser visibility to inventory admins
- ✨ `d8c68bf` feat(purchase_invoice_parser): unificar trigger multisucursal/proveedor, agregar historico en chatter y funcion descartar en OWL
- 🔧 `8d3e827` chore(purchase_invoice_parser): bump version para forzar regeneracion de assets en Odoo.sh
- 🐛 `82e0c6b` fix(purchase_invoice_parser): resolver crash de OWL reemplazando useService('company') obsoleto por el metodo nativo de v19
- 🐛 `b9effbc` fix(purchase_invoice_parser): implementar soporte multisucursal y reactividad real-time en notificaciones de precio
- 🐛 `f8bb363` fix(purchase_invoice_parser): implementar soporte multisucursal y reactividad real-time en notificaciones de precio
- 🐛 `141e74e` fix(purchase_invoice_parser): corregir perdida de contexto this en handler goToProduct de OWL

## 2026-06-14

- ✨ `ed69fa6` feat(purchase_invoice_parser): notificaciones con link al producto, boton aplicar precio y polling
- 🐛 `f32b236` fix(purchase_invoice_parser): corregir trigger de notificaciones de precio y canal de comunicacion del bus
- 🐛 `014b960` fix(purchase_invoice_parser): actualizar campos de seguridad a nomenclatura de Odoo 19 (group_ids/user_ids) para resolver ValueError
- 🐛 `f399af5` fix(purchase_invoice_parser): corregir obtencion de usuarios de grupo por cambio de ORM en Odoo 19
- ✨ `006a7a3` feat(purchase_invoice_parser): implementar centro de notificaciones OWL en el systray para actualizaciones de precios

## 2026-06-12

- 🐛 `14c3db8` fix(purchase_invoice_parser): corregir pre-validación de PDF que bloqueaba XMLs de Brudifarma
- 🔄 `2fb13d8` refactor(purchase_invoice_parser): solucionar error de campo notes y separar estrategias de parseo (XML vs XML+PDF) según proveedor
- 🐛 `96cb214` fix(purchase_invoice_parser): acotar mapeo de moneda y condiciones a supplier_format=brudifarma
- ✨ `310e6a2` feat(purchase_invoice_parser): mapear campos Brudifarma a campos de BD en purchase.order
- ✨ `b0688b7` feat(purchase_invoice_parser): implementar estrategia de parseo adaptativo por RFC y nombre de archivo
- 🐛 `9f5bf80` fix(purchase_invoice_parser): corregir nombre de página en xpath vista partner
- 🐛 `07205b3` fix(purchase_invoice_parser): corregir xpath en vista de proveedor reemplazando ancla custom por campo nativo
- 🐛 `58736ea` fix(purchase_invoice_parser): exponer campo cfdi_supplier_format en formulario de contacto
- 🐛 `3c7bc4d` fix(purchase_invoice_parser): corregir selector de contactos para Odoo 19
- ✨ `091edec` feat(purchase_invoice_parser): derivar formato CFDI desde perfil del proveedor

## 2026-06-11

- ✨ `09f5aca` feat(purchase_invoice_parser): detectar y notificar OC duplicadas en multiempresa
- 🐛 `74a08e0` fix(purchase_invoice_parser, medicine_depot_scrap_batch): corregir validación de unicidad de lotes en entorno multiempresa

## 2026-06-10

- ✨ `6256359` feat(global): agregar i18n/es_MX.po a 11 módulos

## 2026-06-09

- 🐛 `2cafa3d` fix(lots): ocultar company_id y crear lotes globales desde parser de compras

## 2026-06-04

- 🐛 `ec4fef4` fix(lots): implementacion de patron get-or-create para evitar duplicidad de lotes y correccion de asignacion a la mano por sucursal

## 2026-05-20

- 🐛 `22895dc` fix(purchase_invoice_parser): priorizar impuestos con 'compra' en nombre en TaxResolver
- 🐛 `3e6e564` fix(purchase_invoice_parser): restaurar deteccion automatica de BRUDIFARMA por RFC y mostrar formato de proveedor en wizard
- • `10fe1dc` improvement(purchase_invoice_parser): add supplier format selection and CFDI branch logic
- 🔄 `36dce55` refactor(purchase_invoice_parser): enrutamiento dinamico CFDI por RFC
- 🐛 `db42abd` fix(purchase_invoice_parser): agregar title y aria-label en iconos FA
- 🐛 `c84e84f` fix(purchase_invoice_parser): respetar lista de IVA configurada, sin bloqueos
- 🐛 `c621096` fix(purchase_invoice_parser): fallback de IVA por sucursal y aviso en chatter
- 🐛 `b1f7a3a` fix(purchase_invoice_parser): corregir fallback IVA y mejorar robustez del TaxResolver

## 2026-05-19

- 🐛 `f18b771` fix(purchase_invoice_parser): sanitizacion del contexto en _post_chatter eliminando force_company para resolver deprecation warning al publicar mensajes
- 🐛 `706bfbd` fix(purchase_invoice_parser): evitar bloqueo por iva 0% sin impuesto de compras configurado
- 🐛 `b7f117f` fix(purchase_invoice_parser): eliminacion de clave obsoleta force_company en favor de with_company para silenciar DeprecationWarning en odoo 19
- 🐛 `2f7e692` fix(purchase_invoice_parser): extraer iva de brudifarma desde TasaOCuota con fallback global
- 🐛 `5572b2d` fix(purchase_invoice_parser): ocultar boton de extraccion PDF para BRUDIFARMA
- 🐛 `bcaf302` fix(purchase_invoice_parser): priorizar lote de Addenda BRUDIFARMA sobre descripcion y PDF
- 🐛 `7852ae7` fix(purchase_invoice_parser): extraer lotes desde campo Descripcion del CFDI para BRUDIFARMA
- 🔄 `c72719f` refactor(purchase_invoice_parser): refactorización arquitectónica integral (5 fases)
- 🐛 `5923950` fix(invoice_parser): limpiar sufijo de caducidad en lotes de brudifarma
- 🐛 `3a5f138` fix(invoice_parser): priorizar iva de compras en el matching de impuestos por compania destino
- 🐛 `bbf573c` fix(invoice_parser): resolucion de inconsistencia en asignacion de iva para la matriz forzando contexto de compania en la busqueda de account.tax
- 🐛 `9c87373` fix(purchase_invoice_parser): desduplicar lotes addenda BRUDIFARMA y evitar altas por ceros a la izquierda
- 🔧 `7110e17` chore(purchase_invoice_parser): agregar prueba de no-creacion de productos en flujo BRUDIFARMA
- 🐛 `7efdbc4` fix(purchase_invoice_parser): robustecer enlace BRUDIFARMA por referencia y cbarra
- 🐛 `b20f4c3` fix(purchase_invoice_parser): priorizar referencia interna BRUDIFARMA y corregir asignacion IVA
- 🐛 `149a904` fix(purchase_invoice_parser): endurecer addenda y evitar asignaciones ambiguas de lotes
- ✨ `e0e00da` feat(purchase_invoice_parser): auditoria de parseo e implementacion de extraccion de addendas para lotes y caducidad de brudifarma

## 2026-05-16

- 🐛 `e0dfa1e` fix(purchase_invoice_parse): correccion en la asignacion del diccionario de creacion para trasladar el IVA a las lineas del documento en borrador
- ✨ `31aa9dd` feat(purchase_invoice_parser): extraccion de TasaOCuota desde XML CFDI y mapeo automatico de impuestos en lineas de factura

## 2026-05-12

- 🐛 `50b1cad` fix(deps): declarar dependencias python para odoo sh

## 2026-05-04

- • `0d0649f` merge test into main for pos z report deployment
- 🐛 `ad0ebc7` fix(purchase_invoice_parser): remove manual lot creation button
- 🐛 `6d85b24` fix(purchase_invoice_parser): ignore invalid zip pdf entries
- ✨ `1140fbd` feat(purchase_invoice_parser): add zip upload and provider registry
- 📚 `318ec28` docs: add purchase_invoice_parser README with architecture and usage guide
- 📚 `c4e84fe` docs: update documentation with 17 modules and infrastructure metrics
- 🐛 `4fc4f85` fix(purchase_invoice_parser): avoid duplicate lot lines
- 🐛 `e9e115e` fix(purchase_invoice_parser): restore PDF lot review flow

## 2026-04-30

- ✨ `2ee5e2f` feat(purchase_invoice_parser): confirmar manualmente lotes antes de crear la OC
- ✨ `dfee764` feat(purchase_invoice_parser): quitar botones de lotes PDF y soportar descuento previo al lote
- 🐛 `5347802` fix(purchase_invoice_parser): auto-parse PDF — flush antes y errores visibles

## 2026-04-29

- ✨ `52a05d8` feat(purchase_invoice_parser): PDF opcional desde paso 1 + columna Lotes en review
- • `9fc9de2` ux(purchase_invoice_parser): botón Extraer lotes en verde + adjuntar XML/PDF a OC
- • `60816bd` ux(purchase_invoice_parser): paso 1 del wizard centrado con ícono de importar
- ✨ `1169e85` feat(purchase_invoice_parser): botón Importar XML en list de Compras (sustituye menú)
- ✨ `f978cfc` feat(purchase_invoice_parser): propagar lote+caducidad del PDF a líneas de OC
- ✨ `fc4b2ac` feat(purchase_invoice_parser): parser de lotes PDF más tolerante + diagnóstico
- 🐛 `a1c548f` fix(purchase_invoice_parser): asegurar visibilidad del bloque PDF de lotes
- 🐛 `1b35677` fix(purchase_invoice_parser): refuerzo a11y en alert (aria-live, aria-label)
- 🐛 `5e507b5` fix(purchase_invoice_parser): a11y en alert de avisos del parser
- ✨ `08e847d` feat(purchase_invoice_parser): extracción de lotes desde PDF de factura
- 🐛 `51e5e83` fix(purchase_invoice_parser): renombrar taxes_id -> tax_ids en order_line (Odoo 19)
- 🐛 `55b2980` fix(purchase_invoice_parser): quitar campo 'notes' inexistente en purchase.order (Odoo 19)

## 2026-04-28

- 🐛 `9a28de6` fix(purchase_invoice_parser): usar uom_id y product_uom_id (Odoo 19)
- 🐛 `3f4dfb1` fix(purchase_invoice_parser): reemplazar xpath roto por entrada de menú
- ✨ `72e9597` feat(purchase_invoice_parser): nuevo módulo para crear OC desde CFDI 4.0 XML
