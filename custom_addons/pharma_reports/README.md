# pharma_reports — v19.0.1.0.8

**Categoría**: Reporting | **Licencia**: LGPL-3

## Propósito

Suite de reportes PDF farmacéuticos. Proporciona formatos de papel y templates QWeb personalizados para:

- Órdenes de venta (con lotes y fechas de caducidad)
- Órdenes de compra
- Transferencias de stock / albaranes
- Entregas al cliente
- Ajustes de Inventario Físico (stock.quant)

Estos reportes reemplazan los formatos nativos de Odoo con el diseño corporativo de Medicine Depot.

> ⚠️ **Regla de negocio**: En todos los reportes, la columna de inventario físico se denomina **"A la mano"**. Nunca "Disponible", "Stock" ni "Existencias".

## Dependencias

```python
depends = [
    'base', 'web', 'sale_stock', 'purchase',
    'product_expiry', 'lot_selection', 'custom_invoice_format'
]
```

## Reportes incluidos

| Archivo | Reporte / Vista |
|---|---|
| `report/sale_order_report.xml` | Orden de Venta con lotes |
| `report/sale_order_header.xml` | Header corporativo compartido |
| `report/sale_order_paperformat.xml` | Formato de papel (A4, márgenes) |
| `report/purchase_order_report.xml` | Orden de Compra |
| `report/purchase_order_paperformat.xml` | Formato de papel para OC |
| `report/stock_transfer_report.xml` | Transferencia de inventario |
| `report/stock_delivery_report.xml` | Albarán de entrega al cliente |
| `report/report_layout_overrides.xml` | Sobrescritura del layout base de Odoo |
| `report/physical_inventory_report.xml` | Reporte de Ajuste de Inventario Físico (stock.quant) |
| `report/physical_inventory_view.xml` | Mejora de UI en Ajustes de Inventario Físico (renombra On Hand a "A la mano" y muestra categoría) |

## Módulos que dependen de pharma_reports

```
lab_inventory_report
medicine_depot_scrap_batch
purchase_order_report (bridge)
sale_lot_report (bridge)
```

## Notas técnicas

- Este módulo no tiene carpetas `models/`, `views/`, `security/` en la raíz — toda la lógica está en `report/`
- Los templates usan `t-call` al header compartido para uniformidad de marca
- `report_layout_overrides.xml` deshabilita el header/footer nativo de Odoo en los reportes afectados
- Score 5/10 en auditoría previa — pendiente mejorar la estructura de carpetas y agregar `models/__init__.py`

## Módulos bridge

`purchase_order_report` y `sale_lot_report` son módulos vacíos que solo declaran `depends = ['pharma_reports']` para preservar compatibilidad con instalaciones antiguas.

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: pharma_reports]
