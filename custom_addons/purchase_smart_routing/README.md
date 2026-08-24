# purchase_smart_routing — v19.0.3.0.0

**Categoría**: Inventory/Purchase | **Licencia**: LGPL-3

## Propósito

Motor de enrutamiento inteligente de compras. Dado un catálogo de demanda, determina automáticamente qué proveedor ofrece el mejor precio para cada producto, considerando:

- N proveedores configurados por producto
- Umbral de precio mínimo (descarta ofertas por debajo del costo)
- **Fuzzy matching** para emparejar nombres de productos de catálogos externos con los registros de Odoo
- Importación de catálogos desde Excel (Levic, Farmater, Brudifarma, etc.)

## Dependencias

```python
depends = ['purchase', 'stock', 'product']
```

## Modelos

| Modelo | Archivo | Propósito |
|---|---|---|
| `product.supplierinfo` | `models/product_supplierinfo.py` | Extensión de info de proveedor con campos de routing |
| `purchase.routing` | `models/purchase_routing.py` | Resultado del enrutamiento por producto |
| `res.config.settings` | `models/res_config_settings.py` | Configuración: umbral precio, algoritmo matching |

## Engine

### `engines/routing_engine.py`

Contiene la lógica central de enrutamiento:

```python
class RoutingEngine:
    def compute_best_supplier(self, product, demand_qty, date=None):
        """Retorna el proveedor con mejor precio para el producto y cantidad dados."""
```

## Wizards

| Wizard | Propósito |
|---|---|
| `supplier_catalog_import` | Importar catálogo de precios desde Excel |
| `routing_demand_import` | Importar lista de demanda desde Excel |
| `routing_catalog_compare` | Comparar catálogos: precio actual vs. proveedor alternativo |

## Vistas

- `views/purchase_routing_views.xml` — Lista y formulario de enrutamiento
- `views/product_supplierinfo_views.xml` — Info de proveedor extendida
- `views/routing_catalog_compare_views.xml` — Comparador de catálogos
- `views/menu.xml` — Menú en **Compras > Enrutamiento**

## Uso típico

1. Importar catálogo de proveedor (Wizard **Importar Catálogo**)
2. Importar lista de demanda (Wizard **Importar Demanda**)
3. Ejecutar **Calcular Enrutamiento**
4. Revisar y aprobar las órdenes de compra sugeridas

## Notas técnicas

- El fuzzy matching usa `difflib.SequenceMatcher` con umbral configurable (default 85%)
- Compatible con múltiples compañías (el enrutamiento es por `company_id`)
- Los catálogos importados se almacenan en `product.supplierinfo` estándar de Odoo

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: purchase_smart_routing]
