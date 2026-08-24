# sale_discount_policy — v19.0.1.2.0

**Categoría**: Sales/Sales | **Licencia**: LGPL-3

## Propósito

Motor de descuentos automáticos para el grupo **Farmacias Económicas**: aplica un descuento del **2%** en todas las líneas de venta y POS para clientes de este grupo, con las siguientes excepciones:

- **SKUs restringidos**: productos de marcas que excluyen descuentos (importables desde Excel)
- **Scope por compañía**: el descuento solo aplica en la empresa configurada
- No afecta a clientes de otros grupos de precio

## Dependencias

```python
depends = ['sale', 'sale_management', 'product', 'stock']
```

## Modelos

| Modelo | Archivo | Propósito |
|---|---|---|
| `sale.discount.policy` | `models/sale_discount_policy.py` | Configuración de políticas de descuento |
| `sale.order.line` | `models/sale_order_line.py` | Aplicación del descuento en líneas |
| `sale.restricted.sku` | `models/sale_restricted_sku.py` | Lista de SKUs excluidos del descuento |
| `product.template` | `models/product_template.py` | Flag de producto restringido |
| `pos.order.line` | `models/pos_order_line.py` | Descuento en líneas POS |

## Engine

### `engines/discount_engine.py`

Lógica central del descuento:

```python
class DiscountEngine:
    def compute_discount(self, partner, product, company):
        """Retorna % de descuento a aplicar (0.0 si no aplica)."""
```

## Datos de configuración

| Archivo | Contenido |
|---|---|
| `data/discount_policy_data.xml` | Política base del 2% |
| `data/partner_category_data.xml` | Categoría "Farmacias Económicas" |
| `data/product_tag_data.xml` | Tag "Marca Restringida" |
| `data/restricted_sku_data.xml` | SKUs restringidos iniciales |

## Wizards

### `wizards/restricted_product_import.py`
Importa lista de SKUs restringidos desde Excel. Accesible en **Ventas > Configuración > SKUs Restringidos**.

## Reporte

`report/discount_verification_report.xml` — PDF de verificación de descuentos aplicados en un periodo.

## Tests

```bash
pytest sale_discount_policy/tests/ -v
```

Cubre: motor de descuento, aplicación en órdenes de venta, exclusión de SKUs restringidos.

## Seguridad

```
sale_discount_policy.group_discount_manager — Configurar políticas y SKUs restringidos
```

## Notas técnicas

- El descuento se aplica al confirmar la orden (`action_confirm`), no en tiempo real al agregar líneas
- Los SKUs restringidos son validados contra `default_code` y `barcode`
- Compatible con listas de precio de Odoo (`pricelist`): el descuento se acumula, no reemplaza

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: sale_discount_policy]
