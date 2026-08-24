# pos_sale_fk_guard — v19.0.1.0.0

**Categoría**: Point of Sale | **Licencia**: LGPL-3

## Propósito

Módulo de protección que previene errores de `ForeignKeyViolation` en PostgreSQL cuando el POS envía referencias `sale_order_line_id` obsoletas o eliminadas.

Esto ocurre cuando:
1. Una orden de venta es cancelada o eliminada
2. El POS (caché del navegador) aún mantiene referencias a esas líneas
3. Al sincronizar, Odoo intenta insertar una FK que ya no existe en la tabla

## Dependencias

```python
depends = ['pos_sale']
```

## Modelos

### `pos.order` (extensión)

Sobreescribe el método de creación/sincronización de órdenes POS para limpiar las referencias `sale_order_line_id` inválidas antes de intentar la inserción en BD.

```python
# Comportamiento
if sale_order_line_id and not line_exists(sale_order_line_id):
    sale_order_line_id = False  # Nullify stale FK
```

## Notas técnicas

- Es un módulo de corrección de bug específico de Odoo 19 + `pos_sale`
- No genera vistas ni datos
- Debe instalarse siempre que `pos_sale` esté activo en el entorno

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: pos_sale_fk_guard]
