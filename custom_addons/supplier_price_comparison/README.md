# supplier_price_comparison — v19.0.1.0.0

**Categoría**: Inventory/Purchase | **Licencia**: LGPL-3

## Propósito

Consolida y compara precios de múltiples proveedores (Levic, Farmater, Brudifarma) importando sus catálogos Excel a un archivo base unificado. Permite al área de compras identificar rápidamente el proveedor más económico para cada producto.

Este módulo es la base de datos de precios que usa `medicine_depot_supplier_import` para actualizar los costos en Odoo.

## Dependencias

```python
depends = ['base', 'purchase']
```

## Modelos

### `price.comparison`

Tabla de comparación de precios: un registro por producto × proveedor, con columnas de precio vigente, precio anterior y variación.

## Services

| Servicio | Propósito |
|---|---|
| `services/supplier_price_consolidator.py` | Motor principal: lee Excel, normaliza, consolida |
| `services/excel_utils.py` | Utilidades de lectura/escritura de Excel (openpyxl) |

## Wizards

| Wizard | Propósito |
|---|---|
| `import_supplier_catalog` | Importar catálogo de UN proveedor (Excel) |
| `import_base_catalog` | Importar o actualizar el catálogo base consolidado |
| `consolidate_supplier_prices` | Ejecutar consolidación completa: todos los proveedores vs. base |

## Vistas

- `views/price_comparison_views.xml` — Lista y pivot de comparación de precios
- `views/menu.xml` — Menú en **Compras > Catálogos > Comparación de Precios**

## Flujo de uso

1. Recibir catálogos Excel de proveedores (Levic, Farmater, Brudifarma)
2. Importar cada catálogo con **Importar Catálogo de Proveedor**
3. Ejecutar **Consolidar Precios** para generar la tabla comparativa
4. Revisar variaciones y decidir qué proveedor usar para cada producto

## Notas técnicas

- Los archivos Excel de proveedores tienen formatos heterogéneos — el consolidador usa `fuzzy matching` para normalizar nombres de productos
- Requiere `openpyxl` instalado en el entorno Python
- La vista pivot de comparación permite agrupar por categoría de producto, laboratorio y proveedor

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: supplier_price_comparison]
