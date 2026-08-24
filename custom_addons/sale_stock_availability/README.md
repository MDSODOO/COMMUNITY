# sale_stock_availability — v19.0.3.2.0

**Categoría**: Sales/Sales | **Licencia**: LGPL-3

## Propósito

Restringe el catálogo de ventas a productos que tienen existencia **A la mano** en el almacén activo. Adicionalmente, limita las cantidades en líneas de OV al inventario real, evitando ventas que excedan lo que físicamente está disponible.

> ⚠️ **Regla de negocio**: La cantidad física de inventario SIEMPRE se denomina **"A la mano"**. Nunca "Disponible", "Stock" ni "Existencias".

## Dependencias

```python
depends = ['sale_stock', 'stock', 'product', 'bus']
```

## Modelos

| Modelo | Archivo | Propósito |
|---|---|---|
| `sale.order` | `models/sale_order.py` | Validación de disponibilidad al confirmar |
| `sale.order.line` | `models/sale_order_line.py` | Restricción de cantidad máxima A la mano |
| `product.product` | `models/product_product.py` | Cómputo de qty_on_hand filtrado por almacén |

## Comportamiento

1. **Al agregar una línea de OV**: La cantidad máxima se limita automáticamente a la cantidad **A la mano** del almacén del vendedor.
2. **Al confirmar la OV**: Se verifica nuevamente la disponibilidad. Si la cantidad A la mano cayó entre la creación y la confirmación, se muestra una advertencia.
3. **Actualización en tiempo real**: Usa el bus de Odoo (`bus`) para refrescar las cantidades A la mano sin recargar la página.

## Assets estáticos

| Ruta | Contenido |
|---|---|
| `static/src/js/` | Componente OWL para actualización en tiempo real |

## Tests

```bash
pytest sale_stock_availability/tests/test_sale_stock_availability.py -v
```

## Notas técnicas

- La cantidad A la mano se calcula con `product.product.qty_available` filtrado por `warehouse_id`
- El módulo `bus` se usa para `longpolling` — la actualización en tiempo real puede desactivarse en configuración
- No impide ventas con backorder; solo advierte al usuario

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: sale_stock_availability]
