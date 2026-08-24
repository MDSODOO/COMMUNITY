# stock_custom — v19.0.99.0.0 (Bridge)

**Categoría**: Tools | **Tipo**: Módulo bridge de compatibilidad

## Propósito

Alias de compatibilidad hacia `lot_selection`. Adicionalmente incluye una vista de `stock.move.line` personalizada heredada del módulo original.

**La lógica principal de lotes está en [`lot_selection`](../lot_selection/README.md).**

```python
depends = ['lot_selection']
```

## Vista adicional

`views/stock_move_line_views.xml` — Columnas adicionales en la lista de líneas de movimiento de stock (lote, fecha de caducidad, destino).

La versión `99` indica que este es un módulo bridge permanente — no se espera evolución funcional.

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: stock_custom]
