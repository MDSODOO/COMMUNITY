# lab_inventory_report — v19.0.1.0.0

**Categoría**: Inventory/Reporting | **Licencia**: LGPL-3

## Propósito

Reporte mensual de inventario **A la mano** agrupado por laboratorio (fabricante) y sucursal (almacén). Permite al área de compras y gerencia visualizar la concentración de inventario por proveedor/laboratorio.

> ⚠️ **Regla de negocio**: La columna de inventario físico se denomina estrictamente "**A la mano**". Nunca "Disponible", "Stock" ni "Existencias".

## Dependencias

```python
depends = ['product', 'stock', 'pharma_reports']
```

## Modelos

### `report.lab.inventory`

Modelo transitorio (`TransientModel`) que computa el inventario **A la mano** por laboratorio, filtrando por:
- Empresa activa (`company_id`)
- Almacén / sucursal
- Fecha de corte (por defecto: fin del mes actual)

## Vistas

| Archivo | Contenido |
|---|---|
| `views/report_lab_inventory_views.xml` | Lista y filtros del reporte |
| `report/report_lab_inventory_templates.xml` | Template QWeb PDF |

## Datos

| Archivo | Contenido |
|---|---|
| `data/ir_cron_data.xml` | Cron para generación mensual automática |

## Uso

1. Ir a **Inventario > Reportes > Laboratorios A la mano**
2. Seleccionar mes y sucursal
3. Hacer clic en **Generar PDF**

O esperar el cron mensual automático (primer día de cada mes, 08:00 AM).

## Notas técnicas

- Hereda la lógica de formato de papel de `pharma_reports`
- Agrupa por `product.template.x_studio_laboratorio` (campo Studio)
- El cron genera y envía el reporte por correo a los responsables configurados

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: lab_inventory_report]
