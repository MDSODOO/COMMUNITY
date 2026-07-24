# custom_shop_qty_selector — v19.0.2.19.0

**Categoría**: Website/Website | **Licencia**: LGPL-3

## Propósito

Mejora la experiencia de compra en la tienda online (`/shop`) con dos componentes:

1. **Qty pill**: Selector de cantidad estilo "pill" en la cuadrícula de productos (vista de tienda).
2. **Badge "A la mano"**: Muestra la cantidad física disponible del producto directamente en la tarjeta de la cuadrícula y en la caja de producto de la página de detalle.

> ⚠️ **Regla de negocio**: La cantidad de inventario físico SIEMPRE se muestra como "**A la mano**". Nunca "Disponible", "Stock" ni "Existencias".

## Dependencias

```python
depends = ['website_sale', 'website_sale_stock', 'website_sale_wishlist']
```

## Modelos

### `product.template` (extensión)
Agrega cómputo del campo `x_qty_on_hand` visible en la tienda, filtrado por compañía activa.

### `website` (extensión)
Configura comportamiento del selector por tienda.

## Controllers

### `controllers/main.py`
Extiende los controllers de `website_sale` para inyectar datos de cantidad **A la mano** en las respuestas JSON del catálogo.

## Vistas

| Archivo | Contenido |
|---|---|
| `views/templates.xml` | Herencia QWeb sobre `website_sale.products` y `website_sale.product` |

## Assets estáticos

| Ruta | Contenido |
|---|---|
| `static/src/scss/` | Estilos del selector pill y badge A la mano |
| `static/src/js/` | Lógica de actualización dinámica del selector |

## Tests

```bash
pytest custom_shop_qty_selector/tests/test_stock_qty.py -v
pytest custom_shop_qty_selector/tests/test_shop_public_access.py -v
```

## Notas técnicas

- Usa `website_sale_stock` para acceder a `product.product.virtual_available` pero lo muestra como "**A la mano**"
- El qty pill es accesible (ARIA labels correctos)
- Compatible con wishlist: no interfiere con el botón de lista de deseos

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: custom_shop_qty_selector]
