# Importador de Costos de Proveedores
**medicine_depot_supplier_import**

## Descripción

Módulo de Odoo 19 que permite importar y actualizar costos de productos desde archivos Excel. Diseñado específicamente para cargar el catálogo de costos de Quifamesa desde `listado_quifa_con_costos-3.xlsx`.

## Características

- **Importación flexible de Excel**: Soporta archivos `.xlsx` y `.xls` con columnas configurables
- **Vista previa antes de importar**: Modo preview para revisar cambios sin afectar el sistema
- **Auditoría completa**: Registro detallado de cada importación con histórico de cambios
- **Validación robusta**: 
  - Normalización automática de códigos de barras
  - Validación de costos (numéricos, positivos)
  - Detección de productos no encontrados
  - Mensajes de error descriptivos por fila
- **Seguridad estricta**: Acceso exclusivo para administradores

## Instalación

```bash
# En tu directorio de módulos Odoo
cd /path/to/odoo/addons
git clone <repo> medicine_depot_supplier_import

# En Odoo, ir a Apps → Actualizar lista de aplicaciones
# Buscar "Importador de Costos de Proveedores" e instalar
```

## Dependencias

- `openpyxl>=3.0`: Para leer archivos XLSX
- `xlrd>=2.0`: Para leer archivos XLS (opcional)

Instaladas automáticamente al instalar el módulo.

## Uso

### 1. Acceder al wizard

Compras → Importador de Costos → Importar Costos de Quifamesa

### 2. Cargar archivo Excel

```
Archivo Excel: listado_quifa_con_costos-3.xlsx
Fila de encabezados: 1
```

### 3. Configurar columnas

Por defecto:
- **Código de barras**: Columna `A` (Principal)
- **Costo unitario**: Columna `H` (u.costo)
- **Descripción**: Columna `C` (Articulo)

Puedes cambiar esto si tu archivo tiene otra estructura.

### 4. Vista previa

Haz clic en "Vista Previa" para analizar el archivo:

```
✅ Análisis completado

Total de líneas: 2507
Líneas válidas: 2450
Productos a actualizar: 2400
Productos no encontrados: 50
Errores: 7
```

Revisa la tabla con los detalles de cada fila.

### 5. Importar

1. Cambia el modo a "Actualizar costos en el sistema"
2. Haz clic en "Importar"
3. El sistema actualiza los costos en `price.comparison.product.quifa_cost`
4. Se genera un log de auditoría

## Modelos

### Wizard (Transient)
- **`supplier.cost.import.wizard`**: Wizard principal de importación
- **`supplier.cost.import.wizard.line`**: Líneas de preview

### Registros (Regular)
- **`supplier.cost.import.log`**: Histórico de importaciones
- **`supplier.cost.import.log.line`**: Detalle de cambios por importación

## Servicios

### `quifa_cost_parser.py`
Servicio de parsing de archivos Excel:

- `read_excel(file_binary, filename)`: Lee archivo XLSX/XLS
- `parse(file_binary, filename, col_barcode, col_cost, col_name, header_row)`: Parsea y valida datos
- Dataclasses: `CostImportLine`, `CostImportResult`

Ejemplo:

```python
from medicine_depot_supplier_import.services.quifa_cost_parser import QuifaCostParser

parser = QuifaCostParser(env)
result = parser.parse(
    file_binary=file_data,
    filename='listado_quifa_con_costos-3.xlsx',
    col_barcode='A',
    col_cost='H',
    col_name='C',
    header_row=1
)

print(f"Líneas válidas: {result.valid}")
for line in result.lines:
    print(f"  Fila {line.row_number}: {line.barcode} → ${line.cost}")
```

## Seguridad

### Grupo de acceso
- **`medicine_depot_supplier_import.group_supplier_cost_import_admin`**: Administradores del módulo

### Permisos
- Solo usuarios en el grupo `base.group_system` (Administradores) pueden:
  - Acceder al wizard
  - Ver y crear logs de importación

### Control de acceso por modelo
```csv
model_supplier_cost_import_wizard → group_supplier_cost_import_admin (CRUD)
model_supplier_cost_import_log → group_supplier_cost_import_admin (CRUD)
model_supplier_cost_import_log_line → group_supplier_cost_import_admin (CRUD)
```

## Estructura de archivos Excel esperada

### Formato recomendado
```
Fila 1 (Encabezados):
A: Principal | B: Alterna | C: Articulo | ... | H: u.costo

Fila 2+:
70200534702 | | CINTA MICROPORE BCA 5 CM X 9.1 M | ... | 197.95
```

### Reglas de validación
1. **Código de barras** (Col A):
   - No puede estar vacío
   - Mínimo 4 caracteres
   - Se normaliza automáticamente (se convierte a string, elimina .0)

2. **Costo** (Col H):
   - Debe ser numérico (int o float)
   - Debe ser positivo (> 0)
   - Se valida antes de importar

3. **Descripción** (Col C):
   - Se usa solo para los registros en preview
   - Opcional para productos encontrados

## Flujo de trabajo

```
┌─────────────────────────────────────────┐
│ 1. Cargar archivo Excel                 │
├─────────────────────────────────────────┤
│ 2. Configurar columnas (A, H, C)        │
├─────────────────────────────────────────┤
│ 3. Ejecutar "Vista Previa"              │
│    - Valida formato y buscas productos  │
│    - Muestra estadísticas               │
│    - Detalla errores por fila           │
├─────────────────────────────────────────┤
│ 4. Revisar cambios en tabla             │
│    - ✅ Válidos (verde)                 │
│    - ⚠️  No encontrados (amarillo)      │
│    - ❌ Errores (rojo)                  │
├─────────────────────────────────────────┤
│ 5. Cambiar modo a "Actualizar"          │
├─────────────────────────────────────────┤
│ 6. Hacer clic en "Importar"             │
│    - Actualiza price.comparison.product │
│    - Crea log de auditoría              │
│    - Retorna confirmación               │
└─────────────────────────────────────────┘
```

## Resolución de problemas

### Error: "No se encontró la columna 'A'"
Verifica que tu archivo tiene encabezados en la fila indicada. Cambia la "Fila de Encabezados" si es necesario.

### Error: "Costo inválido"
- El valor en la columna de costo no es un número
- El costo es negativo o cero
- Verifica el formato del archivo

### Error: "Se requiere librería openpyxl"
```bash
pip install openpyxl
# En Odoo: reinicia el servidor
```

### Productos no encontrados
Los códigos de barras no coinciden con los del catálogo base (`price.comparison.product`).

Solución:
1. Primero importa el catálogo base usando `supplier_price_comparison`
2. Verifica que los códigos en el Excel sean idénticos (sin espacios, ceros a la izquierda, etc.)

## Ejemplo: Importar desde Python

```python
# En consola Odoo
wizard = env['supplier.cost.import.wizard'].create({
    'file': base64_file_data,
    'filename': 'listado_quifa_con_costos-3.xlsx',
    'col_barcode': 'A',
    'col_cost': 'H',
    'col_name': 'C',
    'header_row': 1,
    'mode': 'preview',
})

# Preview
wizard.action_preview()
print(wizard.result_message)

# Importar
wizard.mode = 'update'
wizard.action_import()
print(wizard.result_message)
```

## Auditoría

Todos los cambios se registran en `supplier.cost.import.log`:

```
Fecha: 2026-05-28 10:30:00
Usuario: Daniel Cervera
Total de líneas: 2507
Productos actualizados: 2400
No encontrados: 50
Errores: 7

Detalle (supplier.cost.import.log.line):
- Fila 2: Código 70200534702 → Actualizado (197.95 → 199.95)
- Fila 3: Código 70200534703 → No encontrado
- ...
```

## Licencia

LGPL-3

## Autor

Daniel Cervera / QUIFAMESA
