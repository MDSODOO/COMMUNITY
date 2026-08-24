# 💡 EJEMPLOS DE USO

## Ejemplo 1: Flujo Completo Manual

### Paso 1: Preparar archivo Excel
```
listado_quifa_con_costos-3.xlsx
├── Row 1: Principal | Alterna | Articulo | ... | u.costo
├── Row 2: 70200534702 | | CINTA MICROPORE... | ... | 197.95
├── Row 3: 70200534703 | | GASA ESTÉRIL... | ... | 45.50
└── ...
```

### Paso 2: Abrir el wizard en Odoo
```
Menú: Compras → Importador de Costos → Importar Costos de Quifamesa
```

### Paso 3: Cargar archivo
```
[Click en campo "Archivo Excel"]
Selecciona: listado_quifa_con_costos-3.xlsx

Formulario se llena:
├── file: [archivo cargado]
├── filename: listado_quifa_con_costos-3.xlsx
├── col_barcode: A (default)
├── col_cost: H (default)
├── col_name: C (default)
├── header_row: 1 (default)
└── mode: preview (default)
```

### Paso 4: Vista Previa
```
[Click en botón "Vista Previa"]

Sistema analiza archivo → crea wizard.line records

Resultado:
┌─────────────────────────────────────────────────┐
│ ✅ Análisis completado                           │
│                                                   │
│ Total de líneas: 2507                           │
│ Líneas válidas: 2450                            │
│ Productos a actualizar: 2400                    │
│ Productos no encontrados: 50                    │
│ Errores: 7                                      │
│                                                   │
│ Revisa los cambios en la tabla de abajo...     │
└─────────────────────────────────────────────────┘

Tabla (Tree view, primeras 10 filas):
┌──────┬──────────────┬──────────────────┬────────┬──────┐
│ Fila │ Código       │ Descripción      │ Nuevo  │ État │
├──────┼──────────────┼──────────────────┼────────┼──────┤
│  2   │ 70200534702  │ CINTA MICROPORE  │ 197.95 │ ✅   │
│  3   │ 70200534703  │ GASA ESTÉRIL     │ 45.50  │ ✅   │
│  4   │ 70200534704  │ ALGODÓN 100%     │ 32.10  │ ✅   │
│  5   │ INVALID      │                  │ ---    │ ❌   │
│  6   │ 70200534706  │ PRODUCTO XYZ     │ ---    │ ⚠️   │
│  7   │ 70200534707  │ OTRO PRODUCTO    │ 99.99  │ ✅   │
└──────┴──────────────┴──────────────────┴────────┴──────┘

Leyenda:
✅ = Válido (será actualizado)
⚠️  = Producto no encontrado en catálogo base
❌ = Error de formato/validación
```

### Paso 5: Revisar cambios
```
Hacer scroll en la tabla para ver:
├── Productos que serán actualizados (verde, ✅)
├── Productos no encontrados (amarillo, ⚠️)
└── Filas con error (rojo, ❌)

Ejemplo de fila con error:
Fila 5: Barcode="INVALID", Error="Código de barras inválido"

Ejemplo de fila no encontrada:
Fila 6: Barcode="70200534706", Error="No encontrado en catálogo base"
```

### Paso 6: Importar
```
[Cambiar campo "Modo" a "Actualizar costos en el sistema"]

[Click en botón "Importar"]

Sistema ejecuta update en cada product:
├── product.write({'quifa_cost': new_cost})
├── Crea log entry
├── Crea log.line entries
└── Retorna confirmación

Resultado:
┌──────────────────────────────────────┐
│ ✅ Importación completada exitosamente│
│                                       │
│ Productos actualizados: 2400          │
│ Productos no encontrados: 50          │
│ Errores: 7                            │
│                                       │
│ Se ha registrado un log...            │
└──────────────────────────────────────┘
```

### Paso 7: Verificar en BD
```
# En Odoo, ir a: Compras → Comparador de Precios → Productos Base

Producto: CINTA MICROPORE BCA 5 CM
├── Barcode: 70200534702
├── Costo anterior: 0.0 (antes)
└── Costo nuevo: 197.95 ✅ (actualizado)

# Ver log de importación
Menú: [pendiente - agregar en Fase 4]

Registro de importación:
├── Fecha: 2026-05-28 14:30:00
├── Usuario: Daniel Cervera
├── Archivo: listado_quifa_con_costos-3.xlsx
├── Actualizados: 2400
├── No encontrados: 50
└── Errores: 7
```

---

## Ejemplo 2: Uso Programático (Python)

### Código básico
```python
# En consola Odoo o script

import base64
from medicine_depot_supplier_import.services.quifa_cost_parser import QuifaCostParser

# Leer archivo
with open('/ruta/a/listado_quifa_con_costos-3.xlsx', 'rb') as f:
    file_content = f.read()

file_binary = base64.b64encode(file_content)
filename = 'listado_quifa_con_costos-3.xlsx'

# Parsear
parser = QuifaCostParser(env)
result = parser.parse(
    file_binary=file_binary,
    filename=filename,
    col_barcode='A',
    col_cost='H',
    col_name='C',
    header_row=1
)

# Resultados
print(f"Total: {result.total}")
print(f"Válidas: {result.valid}")
print(f"Errores: {len(result.errors)}")

for line in result.lines[:5]:
    print(f"  Fila {line.row_number}: {line.barcode} = {line.cost}")
```

### Crear wizard programáticamente
```python
# Crear wizard
wizard_vals = {
    'file': file_binary,
    'filename': 'listado_quifa_con_costos-3.xlsx',
    'col_barcode': 'A',
    'col_cost': 'H',
    'col_name': 'C',
    'header_row': 1,
    'mode': 'preview',
}

wizard = env['supplier.cost.import.wizard'].create(wizard_vals)

# Ejecutar preview
wizard.action_preview()
print(wizard.result_message)

# Ver líneas de preview
for line in wizard.preview_lines:
    print(f"{line.barcode}: {line.status} - {line.error_message}")

# Cambiar a modo update
wizard.mode = 'update'

# Importar
wizard.action_import()
print(wizard.result_message)

# Verificar log creado
logs = env['supplier.cost.import.log'].search([], order='date desc', limit=1)
if logs:
    log = logs[0]
    print(f"Log: {log.date}")
    print(f"  Actualizados: {log.updated}")
    print(f"  No encontrados: {log.not_found}")
    print(f"  Errores: {log.errors}")
```

### Filtrar logs
```python
# Obtener logs del último mes
from datetime import datetime, timedelta

date_limit = datetime.now() - timedelta(days=30)

recent_logs = env['supplier.cost.import.log'].search([
    ('date', '>=', date_limit)
], order='date desc')

print(f"Importaciones del último mes: {len(recent_logs)}")

for log in recent_logs:
    print(f"  {log.date}: {log.updated} productos actualizados (usuario: {log.user_id.name})")
```

### Analizar cambios específicos
```python
# Encontrar producto específico en logs
product = env['price.comparison.product'].search([
    ('barcode', '=', '70200534702')
], limit=1)

if product:
    # Buscar cambios históricos
    log_lines = env['supplier.cost.import.log.line'].search([
        ('product_id', '=', product.id),
        ('status', '=', 'updated')
    ], order='log_id desc')
    
    print(f"Histórico de cambios para {product.name}:")
    for line in log_lines:
        log = line.log_id
        print(f"  {log.date}: ${line.old_cost} → ${line.new_cost} "
              f"(cambio: ${line.cost_change})")
```

---

## Ejemplo 3: Validación de Datos

### Verifica que el archivo sea compatible
```python
parser = QuifaCostParser(env)

# Leer archivo
rows = parser.read_excel(file_binary, 'listado_quifa_con_costos-3.xlsx')
print(f"Total de filas: {len(rows)}")

# Extraer headers
headers = rows[0]
print(f"Encabezados: {headers}")

# Verificar columnas
try:
    idx_bc = parser._col_index('A', headers)
    idx_cost = parser._col_index('H', headers)
    idx_name = parser._col_index('C', headers)
    print(f"Columnas encontradas: A={idx_bc}, H={idx_cost}, C={idx_name}")
except UserError as e:
    print(f"Error: {e}")
```

### Detectar problemas en el archivo
```python
# Previsualizar primeros 10 productos problemáticos
result = parser.parse(file_binary, filename, 'A', 'H', 'C', 1)

errors = [l for l in result.lines if l.status != 'ok']
print(f"Filas con error: {len(errors)}")

for line in errors[:10]:
    print(f"  Fila {line.row_number}: {line.status} - {line.error}")
```

---

## Ejemplo 4: Integración con Otros Módulos

### Obtener mejores precios después de importar
```python
# Después de importar costos, actualizar comparador de precios

# Buscar productos sin proveedores
products_without_suppliers = env['price.comparison.product'].search([
    ('supplier_count', '=', 0)
])

print(f"Productos sin precios de proveedores: {len(products_without_suppliers)}")

# Estos podrían ser candidatos para importar catálogos de proveedores
# usando supplier_price_comparison
```

### Exportar cambios a CSV
```python
import csv
from datetime import datetime

# Obtener último log
log = env['supplier.cost.import.log'].search([], order='date desc', limit=1)

if log:
    # Crear archivo CSV
    filename = f"importacion_{log.date.strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Fila', 'Código', 'Descripción', 'Costo Anterior', 'Costo Nuevo', 'Status'])
        
        for line in log.log_lines:
            writer.writerow([
                line.row_number,
                line.barcode,
                line.product_name,
                line.old_cost,
                line.new_cost,
                line.status
            ])
    
    print(f"Exportado: {filename}")
```

---

## Ejemplo 5: Manejo de Errores

### Try-catch en importación
```python
try:
    wizard.action_import()
    print("✅ Importación exitosa")
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    
    # Revisar preview_lines para detalles
    errors = wizard.preview_lines.filtered(lambda l: l.status != 'ok')
    print(f"\nLíneas con error: {len(errors)}")
    for line in errors[:5]:
        print(f"  {line.barcode}: {line.error_message}")
```

### Validación paso a paso
```python
# 1. Validar archivo antes de cargar
if not filename.endswith(('.xlsx', '.xls')):
    raise ValueError("Archivo debe ser .xlsx o .xls")

# 2. Validar tamaño
if len(file_binary) > 15 * 1024 * 1024:  # 15 MB
    raise ValueError("Archivo muy grande (máx: 15 MB)")

# 3. Validar contenido
try:
    result = parser.parse(file_binary, filename)
    if result.total == 0:
        raise ValueError("Archivo no tiene datos válidos")
except UserError as e:
    print(f"Error al parsear: {e}")

# 4. Validar antes de importar
if wizard.products_to_update == 0:
    print("Advertencia: No hay productos para actualizar")
```

---

## Ejemplo 6: Monitoreo y Auditoría

### Dashboard de importaciones
```python
from datetime import datetime, timedelta

# Estadísticas del mes
date_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

logs = env['supplier.cost.import.log'].search([
    ('date', '>=', date_start)
])

total_updated = sum(l.updated for l in logs)
total_errors = sum(l.errors for l in logs)

print(f"Dashboard - Mes actual:")
print(f"  Importaciones realizadas: {len(logs)}")
print(f"  Productos actualizados: {total_updated}")
print(f"  Errores totales: {total_errors}")
print(f"  Por usuario:")

for user in env['res.users'].search([]):
    user_logs = logs.filtered(lambda l: l.user_id == user)
    if user_logs:
        user_updated = sum(l.updated for l in user_logs)
        print(f"    {user.name}: {len(user_logs)} importaciones, {user_updated} productos")
```

---

*Última actualización: 2026-05-28*
