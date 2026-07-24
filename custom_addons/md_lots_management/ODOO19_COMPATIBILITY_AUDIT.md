# ODOO19_COMPATIBILITY_AUDIT — md_lots_management

**Fecha:** 2026-06-04
**Auditor:** Claude Code (Sonnet 4.6)
**Rama:** `test`
**Commit auditado:** `f5eddb0`
**Versión del módulo:** 19.0.1.0.0

---

## Estado General

> ⚠️ **CON RIESGOS** — El módulo es funcional en producción pero contiene un **SyntaxError crítico** en el archivo de tests, APIs deprecadas, y divergencias sustanciales entre el CHANGELOG y el código real.

---

## Paso 1 — Hallazgos Python (`models/`)

### ✅ Correcto

| Ítem | Detalle |
|---|---|
| Herencia | `_inherit = 'stock.lot'` — modelo correcto Odoo 19 (no `stock.production.lot`) |
| Decorador create | `@api.model_create_multi` — correcto para Odoo 17+ |
| Decorador compute | `@api.depends('quant_ids.quantity')` — sintaxis válida |
| Decorador constrains | `@api.constrains(...)` — sintaxis válida |
| `active` field | `fields.Boolean(default=True, tracking=True)` — agregado correctamente |
| Get-or-create | `with_context(active_test=False)` — encuentra lotes archivados, evita duplicados |
| Markup/escape | `markupsafe.Markup` y `escape()` usados correctamente en chatter |
| `action_open_quants` | `type="object"` con `ensure_one()` — patrón correcto |

### ⚠️ Observaciones (no bloquean, pero deben corregirse)

**P-1 — `fecha_ultima_modificacion` es un alias costoso de `write_date`**

```python
# Actual (models/production_lot.py:89-95 y 158-162)
fecha_ultima_modificacion = fields.Datetime(
    compute='_compute_fecha_ultima_modificacion',
    store=True, readonly=True, tracking=True,
)

@api.depends('write_date')
def _compute_fecha_ultima_modificacion(self):
    for lot in self:
        lot.fecha_ultima_modificacion = lot.write_date
```

`write_date` es un campo nativo de `models.Model` con el mismo valor. Esta computed almacenada ocupa una columna PostgreSQL extra y dispara recomputación en cada `write`. Alternativa directa:

```python
# Recomendado
fecha_ultima_modificacion = fields.Datetime(
    string='Última Modificación',
    related='write_date',
    store=False,
    readonly=True,
)
```

**P-2 — `tracking=True` en campo computed `fecha_ultima_modificacion`**

Un campo `computed + store + tracking=True` puede generar doble entrada en el chatter: el tracking de `mail.thread` lo registra Y el ORM puede relanzar el evento de write. No es un bug visible, pero genera ruido en el log.

**P-3 — `_md_tracked_fields` como atributo de clase mutable**

```python
_md_tracked_fields = {  # dict de clase compartido por todas las instancias
    'name': 'Número de serie/lote',
    ...
}
```

Si algún módulo hereda `ProductionLot` y modifica este dict en tiempo de ejecución, afectará a todas las instancias. Patrón más seguro: hacerlo un frozenset o definirlo como propiedad. En el contexto actual (sin subclases) no es problema.

---

## Paso 2 — Hallazgos XML (`views/`)

### ✅ Correcto

| Ítem | Detalle |
|---|---|
| `inherit_id ref="stock.view_production_lot_form"` | ID externo vigente en Odoo 19 |
| `inherit_id ref="stock.view_production_lot_kanban"` | Vigente |
| `inherit_id ref="stock.search_product_lot_filter"` | Vigente |
| `xpath //div[@name='button_box'] position="inside"` | Patrón correcto post-corrección |
| `xpath //group[@name='description'] position="replace"` | Objetivo verificado en arch nativa |
| Sin rastros de `x_studio_` | Limpio — migración completada |
| `menuitem parent="stock.menu_stock_root"` | ID de menú correcto |

### ❌ Error — XML-1: `readonly="1"` sintaxis obsoleta en formulario

```xml
<!-- production_lot_forms.xml:34,47,48 — sintaxis vieja -->
<field name="fecha_entrada" readonly="1"/>
<field name="usuario_creacion" readonly="1"/>
<field name="fecha_ultima_modificacion" readonly="1"/>
```

En Odoo 17+ el compilador de vistas prefiere expresiones Python booleanas. `"1"` funciona pero genera advertencias internas. Corrección:

```xml
<field name="fecha_entrada" readonly="True"/>
```

### ⚠️ XML-2: Vista Kanban con xpath frágil para Odoo 19 OWL

```xml
<!-- production_lot_forms.xml:67-68 -->
<xpath expr="//templates" position="before">
    <field name="cantidad_la_mano"/>
    <field name="estado_lote"/>
</xpath>
```

En Odoo 19 el Kanban usa componentes OWL. `<field>` declarados fuera del bloque `<templates>` via `position="before"` no tienen garantía de renderizado en la capa OWL. Pueden cargarse en el modelo de datos pero no mostrarse. **Verificar visualmente en Odoo.sh.**

### ⚠️ XML-3: Vista Lista standalone sin herencia

`view_production_lot_tree_customized` es una vista independiente (no hereda ninguna vista nativa). Esto significa que si Odoo actualiza su vista lista de `stock.lot` (nuevos campos, decoradores, optimizaciones), nuestra vista no recibe esos cambios automáticamente.

Riesgo: aislamiento a largo plazo. Aceptable si las columnas mostradas son intencionales.

### ⚠️ XML-4: `partner_ids` en lista sin condición de visibilidad

```xml
<!-- production_lot_views.xml:19 -->
<field name="partner_ids" string="Transferir a" optional="hide" widget="many2many_tags" />
```

La vista nativa tiene `invisible="not partner_ids or not location_id"` en este campo. La lista standalone no hereda esa condición — el campo puede aparecer con datos vacíos o confusos al habilitarlo con `optional`. Recomendación: agregar `invisible="not partner_ids"` o eliminarlo.

### ⚠️ XML-5: `company_id` forzado invisible en formulario

```xml
<!-- production_lot_forms.xml:20-22 -->
<xpath expr="//sheet//field[@name='company_id']" position="attributes">
    <attribute name="invisible">1</attribute>
</xpath>
```

La vista nativa ya tiene `company_id` con `groups="base.group_multi_company"` (solo visible en instancias multi-empresa). Forzarlo a `invisible=1` incondicionalmente oculta la empresa incluso para administradores en entornos multi-empresa. **Riesgo bajo en instancia single-company**, pero puede ser un problema si Medicine Depot habilita multi-empresa.

---

## Paso 3 — Seguridad y Dependencias

### ✅ `ir.model.access.csv`

```
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_production_lot_user,...,stock.model_stock_lot,base.group_user,1,0,0,0
access_production_lot_inventory,...,stock.group_stock_user,1,1,1,0
access_production_lot_manager,...,stock.group_stock_manager,1,1,1,1
```

- `stock.model_stock_lot` — referencia correcta al modelo en Odoo 19 ✅
- Grupos `stock.group_stock_user` y `stock.group_stock_manager` — vigentes ✅
- `base.group_user` con solo lectura — correcto ✅

### ⚠️ SEC-1: Orden en `data` del manifest

```python
# __manifest__.py:26-30 — actual
'data': [
    'views/production_lot_views.xml',   # ← carga vistas primero
    'views/production_lot_forms.xml',
    'security/ir.model.access.csv',     # ← permisos al final
],
```

Convención Odoo: la seguridad debe cargarse **antes** que las vistas para evitar errores de acceso durante la instalación en entornos estrictos:

```python
'data': [
    'security/ir.model.access.csv',
    'views/production_lot_views.xml',
    'views/production_lot_forms.xml',
],
```

### ✅ Dependencias `__manifest__.py`

| Dependencia | Razón | Estado |
|---|---|---|
| `stock` | Modelo base `stock.lot` | ✅ |
| `product_expiry` | Campo `expiration_date` en `stock.lot` | ✅ |
| `mail` | `tracking=True`, `message_post()` | ✅ |
| `base` | `res.users`, `res.company` | ✅ |

---

## Paso 4 — Hallazgos en Tests (`tests/test_lots_migration.py`)

### ❌ CRÍTICO — TEST-1: SyntaxError en nombre de método (línea 84)

```python
# test_lots_migration.py:84 — ROMPE TODO EL ARCHIVO DE TESTS
def test_03_usuario_creacion_autom ático(self):
#                                ^^^^^ ESPACIO INVÁLIDO en identificador Python
```

**Verificado:** `python3 -c "import ast; ast.parse(open(...))"` → `SyntaxError: expected '(' at line 84`

El archivo de tests **no puede importarse**. Todos los 15 tests del archivo están inaccesibles hasta que se corrija.

### ❌ CRÍTICO — TEST-2: `type='product'` deprecado en Odoo 17+

```python
# test_lots_migration.py:18
cls.product = cls.env['product.product'].create({
    'name': 'Producto Test - Lotes',
    'type': 'product',   # ← INCORRECTO en Odoo 17+/19
    'tracking': 'lot',
})
```

En Odoo 17+ el valor de selección cambió: `'product'` → `'storable'`. En Odoo 19, `type='product'` lanzará `ValueError: Wrong value for product.template.type: 'product'`. Corrección:

```python
'type': 'storable',
```

### ❌ ALTO — TEST-3: APIs deprecadas `flush()` y `refresh()`

```python
# test_lots_migration.py:78-79
lot.flush()    # ← DEPRECADO desde Odoo 16. Eliminado en Odoo 17+
lot.refresh()  # ← DEPRECADO. Usar lot.invalidate_recordset()

# test_lots_migration.py:258
lot.refresh()  # ← ídem
```

En Odoo 19 estos métodos **no existen** en `BaseModel`. Lanzarán `AttributeError`. Correcciones:

```python
# Reemplazar lot.flush() por:
lot.env.flush_all()         # o self.env.flush_all()

# Reemplazar lot.refresh() por:
lot.invalidate_recordset()
```

### ⚠️ MEDIO — TEST-4: `time.sleep(1)` en test transaccional

```python
# test_lots_migration.py:254-255
import time
time.sleep(1)
```

Los tests `TransactionCase` de Odoo corren en transacciones rollback. `write_date` usa el timestamp del servidor PostgreSQL, no el tiempo de Python. El `sleep` no garantiza que `write_date` cambie — depende de la resolución del reloj del servidor. El test puede pasar o fallar de forma no determinista. Recomendación: comparar que `write_date >= create_date` en lugar de esperar un segundo.

### ⚠️ MEDIO — TEST-5: Tests no cubren campo `active`

El campo `active = fields.Boolean` fue agregado recientemente. No hay ningún test que valide:
- Que `active=True` por defecto al crear
- Que archivar (`active=False`) funciona sin error
- Que el get-or-create con `active_test=False` encuentra lotes archivados

### ⚠️ BAJO — TEST-6: Aserción trivial en `test_12`

```python
# test_lots_migration.py:242
self.assertTrue(len(lot_leido) > 0 or len(lot_leido) == 0)  # siempre True
```

Esta aserción es tautológica y no verifica nada. El comentario dice "Depende de permisos configurados" pero no prueba ningún comportamiento real.

---

## Paso 4 — Divergencias con Documentación (CHANGELOG.md)

| Ítem en CHANGELOG | Realidad en código | Severidad |
|---|---|---|
| Filtros preestablecidos: "Lotes Activos, Agotados, Vencidos" | **No existen** en `views/production_lot_views.xml` | Alta |
| Búsqueda por `codigo_proveedor_externo` y `referencia_compra` | **No declarados** en `<view type="search">` | Alta |
| Agrupación por Producto, Estado, Fecha de Entrada | **No declarados** en search view | Alta |
| Pestaña 4 "Movimientos de Inventario" en formulario | **No existe** — solo hay 3 pestañas | Alta |
| Menú "Inventario → Seguimiento → Lotes" | El menuitem apunta a `stock.menu_stock_root` (raíz), no a "Seguimiento" | Baja |
| `active` field y capacidad de archivado | **No documentado** en CHANGELOG | Baja |
| `create()` override solo menciona "usuario_creacion" | Omite el patrón get-or-create y `active_test=False` | Baja |

---

## Plan de Remediación (Action Items)

### 🔴 Prioridad Crítica (bloquean tests y CI)

| # | Archivo | Línea | Acción |
|---|---|---|---|
| AC-1 | `tests/test_lots_migration.py` | 84 | Renombrar `test_03_usuario_creacion_autom ático` → `test_03_usuario_creacion_automatico` |
| AC-2 | `tests/test_lots_migration.py` | 18 | Cambiar `'type': 'product'` → `'type': 'storable'` |
| AC-3 | `tests/test_lots_migration.py` | 78-79, 258 | Reemplazar `lot.flush()` → `self.env.flush_all()` y `lot.refresh()` → `lot.invalidate_recordset()` |

### 🟠 Prioridad Alta (afectan comportamiento o correccion)

| # | Archivo | Línea | Acción |
|---|---|---|---|
| AA-1 | `views/production_lot_views.xml` | 26-40 | Agregar `<field>` de búsqueda para `codigo_proveedor_externo`, `referencia_compra` y filtros para estado `agotado`/`descontinuado` |
| AA-2 | `tests/test_lots_migration.py` | nuevo | Agregar tests para campo `active`: default, archivado, get-or-create con lote archivado |

### 🟡 Prioridad Media (calidad y mantenibilidad)

| # | Archivo | Línea | Acción |
|---|---|---|---|
| AM-1 | `views/production_lot_forms.xml` | 34,47,48 | Cambiar `readonly="1"` → `readonly="True"` |
| AM-2 | `__manifest__.py` | 26-30 | Mover `security/ir.model.access.csv` al inicio del array `data` |
| AM-3 | `models/production_lot.py` | 89-95, 158-162 | Reemplazar campo computed `fecha_ultima_modificacion` por `related='write_date'` |
| AM-4 | `tests/test_lots_migration.py` | 254-255 | Eliminar `time.sleep(1)`; comparar `write_date >= create_date` |
| AM-5 | `views/production_lot_views.xml` | 19 | Agregar `invisible="not partner_ids"` a campo `partner_ids` en lista |

### 🟢 Prioridad Baja (documentación y consistencia)

| # | Archivo | Acción |
|---|---|---|
| AB-1 | `CHANGELOG.md` | Actualizar con estado real: sin filtros/groupby custom, sin tab de movimientos, agregar entrada de `active` field |
| AB-2 | `views/production_lot_forms.xml` | Evaluar `invisible="1"` en `company_id` para escenarios multi-empresa futuros |
| AB-3 | `tests/test_lots_migration.py:242` | Reemplazar aserción trivial en `test_12` por validación real de permiso |
| AB-4 | `i18n/es.po` | Archivo vacío (solo cabecera). Agregar traducciones si se requiere soporte ES explícito |

---

## Resumen Ejecutivo

```
Módulo:    md_lots_management v19.0.1.0.0
Branch:    test @ f5eddb0
Estado:    ⚠️  CON RIESGOS

Python (models/):   ✅ Funcional en producción
                    ⚠️  3 observaciones de calidad

XML (views/):       ✅ Sin ParseErrors activos
                    ⚠️  5 observaciones (1 obsolescencia, 4 calidad)

Seguridad CSV:      ✅ Referencias correctas (stock.model_stock_lot)
                    ⚠️  1 observación (orden en manifest)

Manifest:           ✅ Dependencias completas y correctas

Tests:              ❌ SyntaxError crítico (inaccesibles)
                    ❌ 2 APIs deprecadas/rotas en Odoo 19
                    ⚠️  3 observaciones de calidad

CHANGELOG:          ❌ 4 características documentadas no implementadas

Action Items:       3 críticos | 2 altos | 5 medios | 4 bajos
```

---

*Generado por: Claude Code (Sonnet 4.6) — 2026-06-04*
*Metodología: inspección estática de archivos + verificación de arch nativa vía RPC en Odoo.sh test*
