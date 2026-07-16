# lot_selection — v19.0.1.0.0

**Categoría**: Tools | **Licencia**: LGPL-3

## Propósito

Motor central de selección y asignación de lotes/series en órdenes de venta y compra. Implementa **FEFO automático** (First Expired, First Out) para garantizar que los lotes de menor fecha de caducidad se despachan primero.

Este módulo es la dependencia base de todos los módulos de selección de lotes del proyecto:
- `sale_lot_selection` (bridge)
- `purchase_lot_selection` (bridge)
- `stock_custom` (bridge)
- `medicine_depot_scrap_batch`

## Dependencias

```python
depends = ['sale', 'sale_stock', 'purchase', 'purchase_stock']
```

## Modelos

| Modelo | Archivo | Propósito |
|---|---|---|
| `sale.order` | `models/sale_order.py` | Hook de confirmación: asigna lotes FEFO |
| `sale.order.line` | `models/sale_order_line.py` | Campos de lote seleccionado por línea |
| `purchase.order` | `models/purchase_order.py` | Recepción con asignación de lote |
| `purchase.order.line` | `models/purchase_order_line.py` | Campos de lote por línea de compra |
| `stock.move` | `models/stock_move.py` | Propagación del lote seleccionado al movimiento |
| `stock.picking` | `models/stock_picking.py` | Validación de lotes en albarán |

## Vistas

| Archivo | Contenido |
|---|---|
| `views/sale_order_views.xml` | Columna de lote en líneas de venta |
| `views/purchase_order_view.xml` | Columna de lote en líneas de compra |
| `views/stock_lot_search_views.xml` | Búsqueda avanzada de lotes |

## Lógica FEFO

```python
# Pseudocódigo de selección FEFO
lotes = env['stock.lot'].search([
    ('product_id', '=', product.id),
    ('expiration_date', '!=', False),
], order='expiration_date asc')
# Selecciona el primer lote con qty > 0 y expiration_date más próxima
```

## Notas técnicas

- Los módulos bridge (`sale_lot_selection`, `purchase_lot_selection`) son solo alias — toda la lógica está aquí
- Compatible con `product_expiry` para campos `expiration_date` y `removal_date`
- La migración `19.0.0.9` actualizó las tablas de compatibilidad con Odoo 19

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: lot_selection]
