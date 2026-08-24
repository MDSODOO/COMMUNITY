# sale_purchase_margins — v19.0.2.0.0

**Categoría**: Sales, Purchases | **Licencia**: LGPL-3

## Propósito

Cálculo y visualización de márgenes de ganancia en líneas de venta y compra. Permite al equipo comercial y de compras evaluar la rentabilidad de cada línea directamente en los formularios de OV y OC.

## Dependencias

```python
depends = ['base', 'sale', 'purchase', 'account', 'stock']
```

## Modelos

| Modelo | Archivo | Propósito |
|---|---|---|
| `sale.order.line` | `models/sale_order_line.py` | Campos de margen (importe, %) en línea de venta |
| `purchase.order.line` | `models/purchase_order_line.py` | Costo real vs. precio de venta esperado |
| `product.template` | `models/product_template.py` | Costo estándar del producto para el cálculo |
| `product.product` | `models/product_product.py` | Costo real (AVCO/FIFO) del producto |
| `res.company` | `models/res_company.py` | Configuración de márgenes mínimos por empresa |
| `sale.margin.line.rule` | `models/sale_margin_line_rule.py` | Reglas de alerta: margen mínimo por categoría |
| `stock.picking` | `models/stock_picking.py` | Actualiza margen real al validar la entrega |
| `margin.tools` | `models/margin_tools.py` | Utilidades de cálculo compartidas |

## Vistas principales

- `views/sale_order_view.xml` — Columna de margen en líneas de OV
- `views/purchase_order_view.xml` — Columna de margen en líneas de OC
- `views/product_template_view.xml` — Margen esperado en ficha de producto
- `views/res_config_settings_view.xml` — Configuración de márgenes mínimos

## Reglas de alerta

`sale.margin.line.rule` permite configurar umbrales por categoría de producto. Si el margen calculado es inferior al mínimo, la línea se resalta en rojo en la vista de OV.

## Fórmula

```
margen_porcentaje = (precio_venta - costo) / precio_venta * 100
```

## Tests

```bash
pytest sale_purchase_margins/tests/test_margin_computation.py -v
```

## Notas técnicas

- El costo usado en el cálculo es `product.product.standard_price` (valoración AVCO/FIFO según configuración)
- Al validar el albarán, el margen real se recalcula con el costo de la valoración de movimiento
- Compatible con multi-compañía: cada empresa tiene sus propios umbrales de margen

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: sale_purchase_margins]
