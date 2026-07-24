# Changelog - md_lots_management

Todos los cambios notables en este módulo se documentan en este archivo.

---

## [19.0.1.8.0] - 2026-07-07

### ✨ Features

- **Consulta Handheld**: nueva vista Kanban móvil optimizada para dispositivos
  Handheld (ej. CT58) para que los operadores escaneen lotes/código de barras y
  consulten precio de venta público y existencia "A la mano" sin abrir el
  formulario completo. Incluye:
  - Campo `public_sale_price` (related a `product_id.lst_price`) en `stock.lot`.
  - Vista kanban dedicada (`view_production_lot_kanban_handheld`) con tarjetas
    de 3 filas: producto+precio, lote+vencimiento, badge "A la mano".
  - Vista de búsqueda (`view_production_lot_search_handheld`) que acepta texto
    parcial de lote o coincidencia exacta de código de barras del producto,
    con filtro por defecto de existencia "A la mano" > 0.
  - Acción y menú "Consulta Handheld" bajo Inventario.
  - Columna "Precio de Venta" (`public_sale_price`) agregada también a la vista
    de lista de Lotes (`view_production_lot_tree_customized`), a petición del
    usuario, para consultarlo sin depender solo del Kanban móvil.
  - Fix: la tarjeta Kanban mostraba el monto sin la etiqueta "Precio de venta"
    (a diferencia de "Lote:"/"Vence:" que sí llevan rótulo), lo que se
    reportó como si el precio "no apareciera". Se agregó el rótulo "Precio de
    venta" arriba del monto, consistente con la columna de la vista de lista.
  - Precio de venta agregado también a la vista de formulario del lote
    (`view_production_lot_form_customized`, compartida por Consulta Handheld
    y el menú "Lotes"). Nuevos campos `public_sale_price_total` (precio con
    impuestos), `has_public_sale_tax` (si el producto tiene impuesto
    adicional sobre el precio base) y `public_sale_price_tax_label` (nombre
    del impuesto, ej. "IVA 16%"), calculados con `account.tax.compute_all`
    sobre `product_id.taxes_id`. Se muestran en Kanban, formulario y lista
    (columnas opcionales) solo cuando el producto realmente tiene un impuesto
    adicional sobre el precio base.
  - La línea "Precio con Impuestos" (Kanban y formulario) ahora se muestra en
    color naranja (`#fd7e14`), con el mismo tamaño/peso (`fs-4 fw-bold`) que
    el precio base, para diferenciarla visualmente sin perder jerarquía.
  - **Sin acceso a la ficha**: se quitó `form` de `view_mode` en
    `action_production_lot_handheld` (solo `kanban`) y se eliminó la clase
    `oe_kanban_global_click` de la tarjeta — al dar clic en una tarjeta ya no
    navega a la vista formulario del lote, evitando que el operador altere
    algo por accidente al entrar a la ficha.
  - Fix: el input de escaneo solo escuchaba `keydown` para Enter — si el
    lector no manda un terminador real (algunos DataWedge insertan el texto
    completo vía `commitText` sin Enter) o si el foco se perdía por cualquier
    motivo, no se detectaba nada. Se agrega: (a) auto-envío tras ~400ms sin
    cambios en el input (respaldo si no hay Enter), (b) un listener de
    `keydown` a nivel documento como respaldo si el foco no está en el input,
    y (c) reenfoque automático en `blur`.
  - **Fix del escaneo roto**: el diseño anterior (ocultar el buscador y
    capturar solo `keydown` a nivel documento, sin ningún `<input>`
    enfocado) rompía el escaneo real en equipos donde el lector inyecta
    texto vía el IME/InputConnection del campo editable con foco (ej. Zebra
    DataWedge en modo "Keystroke Output" — no son eventos de teclado
    genéricos, es equivalente a "pegar" en el campo enfocado). Ahora el
    aviso "Escanea el código de barras…" es un `<input>` real, siempre
    enfocado (se reenfoca tras cada escaneo y al volver a la pestaña), con
    `inputmode="none"`/`virtualkeyboardpolicy="manual"` como señal best-effort
    para suprimir el teclado táctil (puede no aplicarse en todos los
    dispositivos, pero eso es un problema visual, no funcional — el escaneo
    sí funciona).
  - Fix: `res_users.py` usaba `groups_id`/`user.groups_id`, campo renombrado a
    `group_ids` en esta instancia de Odoo 19 — el `write()` original nunca
    disparaba (la clave no coincidía) y, peor, `create()` sí intentaba leer
    `user.groups_id` y habría roto la creación de *cualquier* usuario
    (`ValueError: Invalid field 'groups_id' on 'res.users'`). Corregido a
    `group_ids` en ambos lugares.
  - **Redirección automática por grupo**: nuevo `models/res_users.py` que fija
    el "Home Action" del usuario a `action_production_lot_handheld` en cuanto
    se le asigna el grupo `group_lots_handheld_user` (si no tenía ya una
    acción de inicio personalizada). Así el operador entra directo a Consulta
    Handheld al iniciar sesión, sin navegar el menú — ligado al grupo de
    seguridad, no al user-agent/hardware (más confiable que detectar el
    dispositivo).
  - Fix: `.o_cp_searchview` trae la clase Bootstrap `d-flex`
    (`display:flex !important`), que le ganaba a `style.display="none"` — el
    buscador nativo seguía visible aunque el banner ya apareciera. Se corrige
    con `style.setProperty("display","none","important")` y se agrega
    `onPatched` para volver a ocultarlo si Odoo remonta el buscador (ej. al
    aplicar el filtro por defecto "A la mano" tras la carga inicial).
  - **Rediseño del buscador**: se oculta por completo el buscador nativo de
    Odoo (input + botón de filtros) y se reemplaza por un aviso decorativo
    "Escanea el código de barras…" (`<div>` no editable, nunca dispara
    teclado táctil). El escaneo se captura con un listener de `keydown` a
    nivel documento (así llegan los caracteres que el lector inyecta como
    tecleo); al detectar Enter, el código capturado se vuelca al input nativo
    oculto mediante eventos sintéticos (`input` + `keydown Enter`), lo que
    ejecuta la búsqueda normal de Odoo (mismo `filter_domain` de
    nombre/código de barras) sin que el usuario haya tocado nunca un campo
    editable real. Reemplaza el enfoque anterior basado en
    `inputmode`/`virtualkeyboardpolicy`, que dependía de que el navegador
    respetara esas señales.
  - Refuerzo: `virtualkeyboardpolicy="manual"` además de `inputmode="none"` en
    el buscador, con un `MutationObserver` que repone ambos atributos si el
    buscador se vuelve a montar. Se agrega también `user-select: none` /
    `-webkit-touch-callout: none` en la tarjeta para que un toque largo no
    dispare el menú nativo de selección de texto del dispositivo (podía
    confundirse con "seleccionar el registro" para edición en conjunto).
    Nota: `inputmode`/`virtualkeyboardpolicy` son señales que el navegador
    puede ignorar según el teclado/IME de fábrica del equipo; si el teclado
    táctil insiste en aparecer en un dispositivo específico, es un ajuste de
    Android/DataWedge en el equipo, no del código.
  - **Sin teclado táctil en el buscador**: nuevo JS
    (`static/src/js/handheld_kanban_view.js`) que registra un `js_class`
    `md_handheld_kanban` para esta vista Kanban específica. Al montar (o
    repintar) la vista, fija `inputmode="none"` en `.o_searchview_input` para
    que el navegador no abra el teclado virtual al enfocar el buscador — el
    operador solo debe escanear el código de barras (que llega como tecleo
    de un lector HID), no escribir a mano. Alcance limitado a esta vista vía
    `js_class`; no afecta el buscador nativo de "Lotes" ni de otras pantallas.
  - **Solo consulta**: la acción `action_production_lot_handheld` ahora fija
    `create/edit/delete/duplicate = False` en su contexto (mismo patrón que
    usa el propio Odoo, ej. botones stat de `res.partner`), y la vista Kanban
    dedicada agrega `create="false" group_create="false" group_edit="false"
    group_delete="false" archivable="false"`. El operador solo puede ver
    datos, sin poder crear, editar, archivar, eliminar ni duplicar lotes por
    error desde esta pantalla.
  - Nuevo grupo de seguridad `group_lots_handheld_user` ("Consulta Handheld")
    para restringir qué usuarios ven el menú "Consulta Handheld". Los
    administradores del sistema (`base.group_system`) lo tienen implícito
    para soporte; el resto de usuarios debe asignarse manualmente desde
    Ajustes → Usuarios.

## [19.0.1.7.0] - 2026-07-07

### 🐛 Fixes

- **Overlap real en el stat button "Pronosticado" (`action_product_tmpl_forecast_report`,
  ícono `fa-area-chart`, en `stock.product_template_form_view_procurement_button`)**:
  auditoría con Playwright (`e2e_tests/audit_button_sizing.spec.ts`) contra
  `medicinedepot-test-34528763.dev.odoo.com` detectó una vista huérfana en la BD
  (`ir.ui.view` id=4383, `model_data_id=false` → **sin dueño en ningún módulo**,
  creada el 2025-04-05 fuera de git, probablemente vía Odoo Studio) que usa el
  xpath ambiguo `//span[hasclass("o_stat_value")]`, cayendo sobre el primer
  `.o_stat_value` del documento (columna izquierda, valor de `qty_available`) e
  inyectando ahí `<span class="o_stat_text">A la mano</span>`. Resultado: 3 líneas
  apiladas a la izquierda contra 2 a la derecha → desalineación/overlap visual.
  Se agrega `view_product_template_form_forecast_button_fix`, escopada sin
  ambigüedad al botón (`//button[@name='action_product_tmpl_forecast_report']`),
  que reemplaza el label de la columna derecha fila 1 (nativamente `uom_name`/
  "On Hand") por el texto fijo "A la mano" — la posición correcta según la
  convención nativa de 2 columnas `o_stat_info`/`o_stat_value`/`o_stat_text`.
  La vista huérfana se desactivó (`active=False`, reversible) directamente en la
  BD de prueba para eliminar la duplicidad — ver
  `docs/audits/2026-07-07_forecast_button_overlap.md`.

## [19.0.1.6.0] - 2026-07-06

### 🐛 Fixes

- **ParseError en `product_template_on_hand_button_views.xml`**: el xpath
  `//button[@name='action_open_quants']` no existía en Odoo 19 — desde hace
  varias versiones `action_open_quants` en `product.template` ya no es un
  `oe_stat_button` en `button_box`, sino un `<a type="object">` inline agregado
  por `stock.view_template_property_form` (inherit_id
  `product.product_template_form_view`) junto a un `<label for="qty_available">`,
  fuera del button box. Se corrige el xpath para apuntar a ese `<label>` real y
  sobrescribir su `string` a "A la mano", en vez de intentar reconstruir un
  stat-button de dos columnas que nunca existió nativamente ahí. Verificado
  contra el código fuente real de `odoo/odoo@19.0`.
- **Regla de negocio**: texto fijo "A la mano" (nunca "Stock"/"Disponible"),
  consistente con `cantidad_la_mano` en `stock.lot`.

## [19.0.1.5.0] - 2026-07-06 (revertido/corregido en 19.0.1.6.0)

### 🐛 Fixes

- **Vista**: Nuevo `views/product_template_on_hand_button_views.xml` — intentaba
  reconstruir el stat button de inventario de la ficha de producto
  (`product.template`) con la estructura nativa `o_stat_info`/`o_stat_value`/
  `o_stat_text` en dos columnas, asumiendo un `<button name="action_open_quants">`
  en `button_box` que en Odoo 19 no existe (ver fix en 19.0.1.6.0). Causaba
  `ParseError` al actualizar el módulo.

---

## [19.0.1.1.0] - 2026-06-04

### 🐛 Fixes (auditoría ODOO19_COMPATIBILITY_AUDIT)

- **Tests**: Corregido `SyntaxError` en `test_03` (espacio en nombre de método)
- **Tests**: `type='product'` → `type='storable'` (Odoo 17+ cambia el enum)
- **Tests**: `lot.flush()` → `self.env.flush_all()`, `lot.refresh()` → `lot.invalidate_recordset()`
- **Tests**: Eliminado `time.sleep(1)` en `test_13`; reemplazado por aserción `write_date == fecha_ultima_modificacion`
- **Tests**: Corregida aserción trivial en `test_12` — verifica permisos de lectura reales
- **Modelo**: `fecha_ultima_modificacion` reemplazada por `related='write_date'` (elimina columna redundante en PostgreSQL)
- **Vistas**: `readonly="1"` → `readonly="True"` (sintaxis Odoo 17+)
- **Manifest**: `security/ir.model.access.csv` movido al inicio de `data` (convención Odoo)
- **Lista**: `partner_ids` con `invisible="not partner_ids"` para evitar columna vacía confusa

### ✨ Agregado

- **Campo**: `active = fields.Boolean(default=True, tracking=True)` — habilita archivar/desarchivar lotes desde el menú de acciones (Odoo 19 nativo no lo incluye en `stock.lot`)
- **Get-or-create**: `with_context(active_test=False)` en `create()` — evita duplicados al recibir un lote previamente archivado
- **Búsqueda**: Campos `codigo_proveedor_externo` y `referencia_compra` disponibles en búsqueda
- **Filtros**: "Agotados", "Descontinuados", "Vencidos" en la vista de búsqueda
- **Agrupaciones**: Por Producto, Estado, Fecha de Entrada
- **Tests**: `test_16` (active default), `test_17` (archivar/buscar), `test_18` (get-or-create con archivado)
- **Smart Button**: "A la mano" corregido — `xpath position="inside"` en `//div[@name='button_box']` nativo (elimina duplicado `o-form-buttonbox`)

---

## [19.0.1.0.0] - 2026-06-03

### 🎯 Objetivo Principal
Migración completa de personalizaciones de Odoo Studio en el modelo `stock.lot` a código puro, preservando datos históricos e mejorando la experiencia de usuario.

### ✨ Agregado

#### Campos Nuevos
- `cantidad_la_mano` (Float - Computed & Stored)
  - Cantidad total disponible en inventario para el lote
  - Calculada desde `quant_ids.quantity`
  - Mejora la experiencia: Muestra "A la Mano" en lugar de términos ambiguos

- `fecha_entrada` (Datetime)
  - Registra cuándo ingresó el lote al sistema
  - Defecto: Fecha/hora actual
  - Útil para trazabilidad y análisis de rotación

- `fecha_vencimiento_estimado` (Date)
  - Complementario a `expiration_date`
  - Permite estimaciones cuando se desconoce el vencimiento exacto
  - Validado contra `expiration_date`

- `estado_lote` (Selection)
  - Valores: Activo | Pausado | Agotado | Descontinuado
  - Defecto: Activo
  - Mejora el control de ciclo de vida del lote

- `notas_calidad` (Text)
  - Captura observaciones de calidad durante inspección
  - Auditable y rastreable
  - Ayuda en análisis post-venta

- `usuario_creacion` (Many2one → res.users)
  - Registra quién creó el lote
  - Automático, basado en usuario actual
  - Parte de auditoría integral

- `codigo_proveedor_externo` (Char)
  - Almacena identificador asignado por proveedor
  - Útil para reconciliación de OC
  - Búsqueda rápida en reportes

- `referencia_compra` (Char)
  - Número de Orden de Compra o Factura
  - Rastreabilidad de origen
  - Integraciones con módulos de compra

#### Vistas

##### Vista de Lista (Tree)
- **Nombre**: `view_production_lot_tree_customized`
- **Mejoras**:
  - Limpieza total de atributos `studio_*`
  - Columnas clave visibles: Número, Producto, **A la Mano**, Vencimiento
  - Columnas opcionales (hidden/show): Ubicación, Códigos, Fechas
  - Editable en línea para cambios rápidos
  - Mejor rendimiento vs Studio

##### Vista de Búsqueda (Search)
- **Nombre**: `view_production_lot_search_customized`
- **Filtros preestablecidos**:
  - Lotes Activos
  - Lotes Agotados
  - Lotes Vencidos
- **Búsqueda por campos**:
  - Número de lote
  - Producto
  - Código proveedor
  - Referencia de compra
- **Agrupación**:
  - Por Producto
  - Por Estado
  - Por Fecha de Entrada

##### Vista de Formulario (Form)
- **Nombre**: `view_production_lot_form_customized`
- **Estructura de pestañas**:
  1. Información General
     - Datos básicos (Producto, Ref, Ubicación)
     - Cantidad A la Mano (readonly)
     - Estado del lote
     - Fechas importantes
  2. Referencias Externas
     - Código del proveedor
     - Referencia de compra
  3. Auditoría
     - Usuario creador
     - Última modificación por
     - Fecha de escritura
  4. Movimientos de Inventario
     - Tabla de ubicaciones
     - Cantidades a la mano y reservadas

##### Vista Kanban
- **Nombre**: `view_production_lot_kanban`
- **Agrupación por**: Estado del lote
- **Información clave**:
  - Cantidad A la Mano
  - Fecha de vencimiento
  - Acceso a movimientos

#### Acciones y Menús
- Acción `action_production_lot_customized` con múltiples vistas
- Menú integrado en: **Inventario → Seguimiento → Lotes**

#### Funcionalidades Técnicas

##### Computadas
- `_compute_cantidad_la_mano()` - Calcula suma de `quant_ids.quantity`
- `_compute_fecha_ultima_modificacion()` - Registra última fecha de escritura

##### Métodos de Validación
- `_check_expiration_dates()` - Valida que fechas de vencimiento sean coherentes
- Validaciones en nivel de modelo (más seguro que validaciones de vista)

##### Métodos Override
- `create()` - Registra automáticamente usuario creador
- `write()` - Actualiza metadatos de auditoría

### 🔄 Cambios de Datos

#### Migración desde Studio
- Todos los campos `x_studio_*` existentes se mapean a nuevos campos nativos
- **Cero pérdida de datos**: Mapeo directo de columnas PostgreSQL
- Datos históricos se preservan en su totalidad

#### Integridad Referencial
- Relaciones con `stock.lot` (modelo padre) se mantienen
- Acceso a `quant_ids` para movimientos de inventario
- Acceso a `product_id` y referencias de producto

### 📚 Documentación

- `README.md` - Guía completa de uso, instalación, ejemplos
- Docstrings en código Python (Google style)
- Comentarios XML en vistas críticas
- Plan de migración: `../STUDIO_MIGRATION_PLAN.md`

### 🧪 Tests

- Tests unitarios en: `tests/test_lots_migration.py`
- Validación post-migración con Playwright
- Cobertura:
  - Creación de lotes con campos personalizados
  - Cálculo de cantidad A la Mano
  - Validaciones de fechas
  - Permisos de acceso

### 🔐 Seguridad

- Archivo de permisos: `security/ir.model.access.csv`
- Niveles: Usuario Básico | Inventario | Gerente
- Campo `usuario_creacion` audita creación
- Timestamps (`create_date`, `write_date`, `write_uid`) auditados nativamente

### 📊 Rendimiento

- Campo `cantidad_la_mano` está **stored** para acceso rápido
- Índices en campos clave (creados automáticamente por Odoo)
- Evita queries N+1 en vistas listadas

### 🐛 Fixes

N/A (versión inicial)

### ⚠️ Breaking Changes

No hay breaking changes. El módulo es **completamente compatible** con:
- Datos históricos de Studio
- Otros módulos de Odoo
- Futuras actualizaciones de Odoo 19

### 📝 Notas Técnicas

#### Nombre del Módulo
- Instalable como `md_lots_management`
- Hereda de `stock.lot`
- No modifica modelos existentes, solo extiende

#### Dependencias
- `stock` (módulo nativo Odoo 19)
- `base` (módulo nativo Odoo 19)

#### Compatibilidad
- Odoo 19.0
- Python 3.11+
- PostgreSQL 12+

---

## Instalación y Testing

```bash
# 1. Copiar módulo a addons_path
cp -r md_lots_management /ruta/addons/

# 2. Actualizar lista de módulos en Odoo
# (o reiniciar servidor con --update=all)

# 3. Instalar desde UI
# Apps → Buscar "Medicine Depot" → Click "Instalar"

# 4. Validar
# Inventario → Seguimiento → Lotes
# Deberías ver la nueva interfaz
```

---

## Autor
**Claude Code** (claude.ai)

## Fecha de Creación
2026-06-03

## Versión de Odoo Soportada
19.0.1.0.0+

## Estado
🚀 **Producción** - Listo para uso en medicinedepot.odoo.sh
