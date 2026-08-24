# 🏗️ ARQUITECTURA: medicine_depot_supplier_import

## Diagrama de Modelos

```
┌──────────────────────────────────────────────────────────────┐
│                   MODELOS Y RELACIONES                       │
└──────────────────────────────────────────────────────────────┘

MODELOS TRANSIENT (Ephemeral - Sesión del wizard)
═════════════════════════════════════════════════════════

                    supplier.cost.import.wizard
                    (Transient Model)
                    ├── file (Binary)
                    ├── filename (Char)
                    ├── col_barcode (Char) → Ej: "A"
                    ├── col_cost (Char)    → Ej: "H"
                    ├── col_name (Char)    → Ej: "C"
                    ├── header_row (Int)   → Ej: 1
                    ├── mode (Selection)   → 'preview' | 'update'
                    ├── result_message (Text)
                    └── preview_lines (One2many) ──┐
                                                   │
                                    supplier.cost.import.wizard.line
                                    (Transient Model)
                                    ├── wizard_id (Many2one) ←─┤
                                    ├── row_number (Int)
                                    ├── barcode (Char)
                                    ├── product_name (Char)
                                    ├── product_id (Many2one → price.comparison.product)
                                    ├── old_cost (Float)
                                    ├── new_cost (Float)
                                    ├── cost_change (Float, computed)
                                    ├── status (Selection)
                                    └── error_message (Char)


MODELOS REGULARES (Persistent - BD Odoo)
═════════════════════════════════════════

            supplier.cost.import.log
            (Regular Model - Auditoria)
            ├── date (Datetime) ← auto fecha importación
            ├── user_id (Many2one → res.users)
            ├── original_file (Binary) ← archivo guardado
            ├── original_filename (Char)
            ├── total_rows (Int)
            ├── updated (Int)
            ├── not_found (Int)
            ├── errors (Int)
            ├── summary (Text)
            └── log_lines (One2many) ──┐
                                       │
                                    supplier.cost.import.log.line
                                    (Regular Model - Detalle)
                                    ├── log_id (Many2one) ←─┤
                                    ├── row_number (Int)
                                    ├── barcode (Char)
                                    ├── product_name (Char)
                                    ├── product_id (Many2one → price.comparison.product)
                                    ├── old_cost (Float)
                                    ├── new_cost (Float)
                                    ├── cost_change (Float, computed)
                                    ├── status (Selection)
                                    └── error_message (Char)


RELACIÓN CON MÓDULOS EXISTENTES
════════════════════════════════

    price.comparison.product (Módulo supplier_price_comparison)
    ├── barcode (KEY: búsqueda en wizard)
    ├── name
    ├── brand
    ├── quifa_cost ← ACTUALIZADO por este módulo
    └── ...

    res.users
    res.partner (para auditoría)
```

## Flujo de Datos

```
┌──────────────────────────────────────────────────────────────┐
│                    FLUJO DE IMPORTACIÓN                       │
└──────────────────────────────────────────────────────────────┘

PASO 1: Carga de archivo
━━━━━━━━━━━━━━━━━━━━━━━

    Usuario selectiona archivo Excel
            ↓
    Wizard.file = base64_content
    Wizard.filename = "listado_quifa_con_costos-3.xlsx"
            ↓
    Configura columnas (opcional)
    ├── col_barcode = "A"
    ├── col_cost = "H"
    ├── col_name = "C"
    └── header_row = 1


PASO 2: Vista Previa
━━━━━━━━━━━━━━━━━━━

    wizard.action_preview()
            ↓
    QuifaCostParser.parse(file, filename, cols, header_row)
            ↓
    Para cada fila del Excel (desde header_row + 1):
    ├── Validar barcode → normalizar
    ├── Validar cost → float > 0
    ├── Buscar en price.comparison.product por barcode
    ├── Crear supplier.cost.import.wizard.line
    │   ├── status = 'ok' | 'not_found' | 'invalid_cost' | 'error'
    │   ├── product_id = encontrado o NULL
    │   ├── old_cost = producto.quifa_cost
    │   └── new_cost = cost_del_excel
    └── Mostrar KPI strip:
        ├── Productos actualizables (ok + product_id)
        ├── No encontrados (ok + !product_id)
        └── Con error (!ok)


PASO 3: Revisar cambios en tabla
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    [Tree View con decoraciones]
    Fila 2:   70200534702 | CINTA... | 197.95 → 199.95 | ✅ ok
    Fila 3:   70200534703 | GASA...  | --- | ⚠️ no_found
    Fila 4:   ABC | ALGO...   | ERROR | ❌ invalid_cost


PASO 4: Importar (cambiar modo a "update")
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    wizard.mode = 'update'
    wizard.action_import()
            ↓
    Filtrar preview_lines donde status='ok' AND product_id
            ↓
    Para cada línea:
    ├── Crear log_line record (supplier.cost.import.log.line)
    ├── product.write({'quifa_cost': new_cost}) ← ACTUALIZACIÓN
    └── log_line.status = 'updated'
            ↓
    Crear supplier.cost.import.log record
    ├── user_id = env.user
    ├── date = now()
    ├── updated = count(status='ok')
    ├── not_found = count(status='not_found')
    ├── errors = count(otros)
    └── log_lines = [líneas creadas]
            ↓
    Mostrar confirmación: "✅ Importación completada"


PASO 5: Auditoría
━━━━━━━━━━━━━━━━

    supplier.cost.import.log (1 record por importación)
    └── supplier.cost.import.log.line (1 record por fila procesada)
            ├── log_id → log principal
            ├── row_number → fila del Excel
            ├── barcode → código
            ├── product_id → encontrado
            ├── old_cost → antes
            ├── new_cost → después
            ├── status → 'updated' | 'not_found' | 'error'
            └── error_message → detalle de error
```

## Arquitectura de Servicios

```
┌──────────────────────────────────────────────────────────────┐
│                   SERVICIOS Y UTILIDADES                      │
└──────────────────────────────────────────────────────────────┘

CAPAS
═════

┌─────────────────────────────────────────┐
│         PRESENTACIÓN (Vistas XML)       │
│  import_quifa_cost_views.xml            │
│  - Formulario del wizard                │
│  - Tree de preview_lines con colores    │
│  - KPI strip de estadísticas            │
└──────────────────────┬──────────────────┘
                       │ (Models & Methods)
┌──────────────────────▼──────────────────┐
│     LÓGICA DE NEGOCIO (Models ORM)      │
│  - supplier_cost_import.py              │
│  - import_quifa_cost_wizard.py          │
│    ├── action_preview()                 │
│    ├── action_import()                  │
│    └── @computed _compute_statistics()  │
└──────────────────────┬──────────────────┘
                       │ (Service Layer)
┌──────────────────────▼──────────────────┐
│     SERVICIOS (quifa_cost_parser.py)    │
│  - QuifaCostParser class                │
│    ├── read_excel()                     │
│    ├── parse()                          │
│    ├── _normalize_barcode()             │
│    ├── _parse_cost()                    │
│    ├── _col_index()                     │
│    └── Dataclasses:                     │
│        ├── CostImportLine               │
│        └── CostImportResult             │
└──────────────────────┬──────────────────┘
                       │ (External Libs)
┌──────────────────────▼──────────────────┐
│     DEPENDENCIAS EXTERNAS               │
│  - openpyxl (XLSX)                      │
│  - xlrd (XLS)                           │
│  - base64 (encoding)                    │
│  - io (BytesIO)                         │
└──────────────────────────────────────────┘


SERVICIO: QuifaCostParser
═════════════════════════════

    class QuifaCostParser
    │
    ├── def read_excel(file_binary, filename)
    │   │
    │   ├── base64.b64decode(file_binary)
    │   ├── Si .xls → xlrd.open_workbook()
    │   └── Si .xlsx → openpyxl.load_workbook()
    │   └── return [[cell1, cell2, ...], ...]
    │
    ├── def parse(file_binary, filename, col_barcode, col_cost, col_name, header_row)
    │   │
    │   ├── read_excel() → rows
    │   │
    │   ├── _col_index(col_barcode, headers) → idx_bc (0-based)
    │   ├── _col_index(col_cost, headers) → idx_cost
    │   ├── _col_index(col_name, headers) → idx_name
    │   │
    │   ├── Para cada row en rows[header_idx+1:]:
    │   │   ├── _normalize_barcode(row[idx_bc]) → bc o None
    │   │   ├── _parse_cost(row[idx_cost]) → (cost, error)
    │   │   └── crear CostImportLine(row_num, bc, cost, status, error)
    │   │
    │   └── return CostImportResult(lines=[...], total=N, valid=M)
    │
    ├── def _normalize_barcode(raw_value) → barcode or None
    │   └── Maneja: int, float, str → normaliza → valida longitud
    │
    ├── def _parse_cost(raw_value) → (cost or None, error or None)
    │   └── Valida: numérico, positivo, no cero
    │
    └── def _col_index(col_ref, headers) → idx or raises UserError
        └── Busca: "A", "B", "C" (letras) o nombre en headers


DATACLASSES
════════════

    @dataclass
    class CostImportLine:
        row_number: int         ← Número de fila del Excel
        barcode: Optional[str]  ← Código de barras normalizado
        product_name: Optional[str] ← Descripción (opcional)
        cost: Optional[float]   ← Costo parseado
        status: str = 'error'   ← 'ok', 'no_barcode', 'invalid_cost', 'error'
        error: Optional[str]    ← Mensaje de error


    @dataclass
    class CostImportResult:
        lines: list             ← list[CostImportLine]
        total: int              ← Total de líneas procesadas
        valid: int              ← Líneas sin errores
        errors: list            ← Errores no recuperables
```

## Seguridad (ACL)

```
┌──────────────────────────────────────────────────────────────┐
│                  CONTROL DE ACCESO                            │
└──────────────────────────────────────────────────────────────┘

GRUPO DE SEGURIDAD
══════════════════

    group_supplier_cost_import_admin
    └── implied_ids: base.group_system (Administradores)


PERMISOS POR MODELO (ir.model.access.csv)
══════════════════════════════════════════

    ┌────────────────────────────────────────────┐
    │ Modelo                   │ Grupo              │ Perms
    ├────────────────────────────────────────────┤
    │ supplier.cost.import.wizard           │ admin  │ CRUD (1,1,1,1)
    │ supplier.cost.import.log              │ admin  │ CRUD (1,1,1,1)
    │ supplier.cost.import.log.line         │ admin  │ CRUD (1,1,1,1)
    └────────────────────────────────────────────┘

VISIBILIDAD DE MENÚ (security.xml)
═══════════════════════════════════

    Menú "Importador de Costos"
    ├── Visible solo para: group_supplier_cost_import_admin
    └── Debajo de: purchase.menu_purchase_root


FLUJO DE AUTORIZACIÓN
═════════════════════

    Usuario intenta acceder a wizard
            ↓
    ¿Está en base.group_system?
    ├── SÍ → Puede acceder (ACL + XML checks)
    └── NO → Acceso denegado (error 403)

    Usuario intenta acción action_import()
            ↓
    ¿Tiene permiso write en supplier.cost.import.wizard?
    ├── SÍ → Actualiza product.quifa_cost
    └── NO → Acceso denegado

    Usuario intenta ver log
            ↓
    ¿Tiene permiso read en supplier.cost.import.log?
    ├── SÍ → Ve histórico
    └── NO → Acceso denegado
```

## Integración con Módulos Existentes

```
┌──────────────────────────────────────────────────────────────┐
│          DEPENDENCIAS Y RELACIONES CON OTROS MÓDULOS          │
└──────────────────────────────────────────────────────────────┘

medicine_depot_supplier_import (Este módulo)
    │
    ├─► depends: supplier_price_comparison (módulo base)
    │       │
    │       ├── Usa: price.comparison.product
    │       │   └── barcode (clave de búsqueda)
    │       │   └── quifa_cost (campo a actualizar)
    │       │
    │       └── Usa: price.comparison.line
    │           └── (referencia indirecta, para contexto)
    │
    ├─► depends: purchase (módulo Odoo estándar)
    │       └── Usa: res.partner (para auditoría)
    │
    ├─► depends: stock (módulo Odoo estándar)
    │       └── Usa: stock.location, stock.lot (contexto)
    │
    └─► depends: base (módulo Odoo estándar)
            └── Usa: res.users, res.groups


RELACIÓN CONCEPTUAL
════════════════════

    supplier_price_comparison
    ├── price.comparison.product
    │   ├── barcode (PK)
    │   └── quifa_cost ←─── ACTUALIZADO POR
    │                       medicine_depot_supplier_import
    └── price.comparison.line
        ├── supplier_id (Many2one → res.partner)
        └── price


FLUJO INTEGRADO
════════════════

    Fase 1: Importar catálogo base
    ┌─────────────────────────────────┐
    │ supplier_price_comparison       │
    │ action_import_base_catalog()    │
    └──────────────┬──────────────────┘
                   ↓ (crea productos)
        price.comparison.product × 2000
        ├── barcode = "70200534702"
        ├── name = "CINTA MICROPORE..."
        └── quifa_cost = 0.0 (inicial)


    Fase 2: Importar costos (este módulo)
    ┌─────────────────────────────────┐
    │ medicine_depot_supplier_import  │
    │ action_preview() + action_import()
    └──────────────┬──────────────────┘
                   ↓ (busca y actualiza)
        price.comparison.product × 2400
        ├── barcode = "70200534702" (búsqueda)
        └── quifa_cost = 197.95 (actualizado)


    Fase 3: Cargar catálogos de proveedores
    ┌─────────────────────────────────┐
    │ supplier_price_comparison       │
    │ action_import_supplier_catalog()│
    └──────────────┬──────────────────┘
                   ↓ (crea líneas)
        price.comparison.line × 5000
        ├── product_id → product × 2400
        ├── supplier_id → res.partner
        ├── price (del proveedor)
        └── best_price (calculado)
```

## Testing

```
┌──────────────────────────────────────────────────────────────┐
│                   PUNTOS DE PRUEBA                            │
└──────────────────────────────────────────────────────────────┘

UNITARIAS
═════════

    test_quifa_cost_parser.py
    ├── test_normalize_barcode()
    │   ├── Entrada: int/float/str
    │   ├── Salida: barcode normalizado o None
    │   └── Casos: 123, 123.0, "123", "ABC", "", None
    │
    ├── test_parse_cost()
    │   ├── Entrada: cost_raw
    │   ├── Salida: (cost, error)
    │   └── Casos: 1.5, "abc", -1, 0, None
    │
    ├── test_col_index()
    │   ├── Entrada: "A", "H", "Código", "Costo"
    │   ├── Salida: índice 0-based
    │   └── Casos: letras, nombres, no encontrado
    │
    ├── test_read_excel_xlsx()
    │   └── Lee archivo XLSX válido
    │
    ├── test_read_excel_xls()
    │   └── Lee archivo XLS válido
    │
    └── test_parse()
        ├── Excel válido → resultado con líneas válidas
        ├── Excel inválido → UserError
        └── Archivo vacío → UserError


INTEGRACIÓN
═══════════

    test_supplier_cost_import_wizard.py
    ├── test_action_preview()
    │   ├── Carga archivo
    │   ├── Ejecuta preview
    │   ├── Verifica preview_lines creadas
    │   └── Valida estadísticas
    │
    ├── test_action_import()
    │   ├── Ejecuta preview primero
    │   ├── Cambia modo a "update"
    │   ├── Ejecuta import
    │   ├── Verifica productos actualizados
    │   └── Verifica log creado
    │
    ├── test_security_access()
    │   ├── Usuario no-admin → access denied
    │   └── Admin → acceso permitido
    │
    └── test_barcode_matching()
        ├── Barcode normalizado
        ├── Búsqueda en producto
        └── Actualización de cost


CASOS DE BORDE
══════════════

    ├── Archivo vacío → UserError
    ├── Header row > filas totales → UserError
    ├── Columna no existe → UserError
    ├── Barcode vacío → error line (status=no_barcode)
    ├── Costo inválido → error line (status=invalid_cost)
    ├── Producto no encontrado → warning (status=ok, product_id=NULL)
    ├── Actualización parcial → log con estadísticas
    └── Importación múltiple → logs separados (auditoría)
```

## Notas Arquitectónicas

1. **Separación de responsabilidades**:
   - Service (`quifa_cost_parser.py`) → parsing y validación
   - Wizard → orquestación y UI
   - Models → persistencia

2. **Transient vs Regular Models**:
   - Transient: datos de sesión (wizard, preview lines)
   - Regular: datos persistentes (logs, auditoría)

3. **Validación en capas**:
   - QuifaCostParser: validación de datos raw
   - Wizard: validación de búsqueda de productos
   - Model: validación de restricciones ORM

4. **Auditoría sin duplicación**:
   - Log captura: usuario, fecha, cambios
   - Log.line detalla cada fila (row_number, barcode, old/new)
   - No duplica productos, solo referencia

5. **Preview antes de aplicar**:
   - Modo "preview" crea wizard lines (transient)
   - Usuario revisa antes de cambiar a "update"
   - Modo "update" ejecuta actualizaciones reales
