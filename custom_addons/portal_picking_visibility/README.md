# portal_picking_visibility — v19.0.1.1.0

**Categoría**: Inventory/Logistics | **Licencia**: LGPL-3

## Propósito

Expone las transferencias de stock (albaranes) en el portal del cliente. El cliente puede ver el estado de sus entregas directamente en `/my` sin necesidad de contactar al equipo de ventas.

## Dependencias

```python
depends = ['sale', 'stock', 'website_sale', 'portal', 'medicine_depot_portal']
```

## Modelos

| Modelo | Archivo | Propósito |
|---|---|---|
| `sale.order` | `models/sale_order.py` | Expone albaranes asociados al portal |
| `stock.picking` | `models/stock_picking.py` | Visibilidad en portal y campos de estado |

## Controllers

### `controllers/portal.py`
- `GET /my/pickings` — Lista de albaranes del cliente
- `GET /my/pickings/<int:picking_id>` — Detalle de un albarán

## Vistas

| Archivo | Contenido |
|---|---|
| `views/portal_templates.xml` | Página de albaranes en el portal del cliente |

## Seguridad

El acceso a los albaranes en portal está restringido por `sale.order.partner_id` — solo el cliente dueño de la orden puede ver sus propias transferencias.

## Tests

```bash
pytest portal_picking_visibility/tests/test_portal_picking.py -v
```

## Notas técnicas

- Requiere `medicine_depot_portal` para heredar el layout bento del portal
- Solo muestra albaranes en estado `confirmed`, `assigned` o `done`
- Las transferencias internas (almacén a almacén) no se muestran al cliente

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: portal_picking_visibility]
