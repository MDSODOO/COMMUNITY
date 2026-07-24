# medicine_depot_scrap_batch — v19.0.1.1.0

**Categoría**: Inventory/Inventory | **Licencia**: LGPL-3

## Propósito

Gestión de bajas de inventario múltiples (batch scrap) con flujo de aprobación por gerente. Permite registrar múltiples productos vencidos o dañados en una sola orden, validarlos y generar el reporte de baja correspondiente.

Incluye:
- Historial de bajas legacy (importado desde sistema anterior)
- Resumen consolidado 2025

## Dependencias

```python
depends = ['stock', 'product_expiry', 'purchase', 'lot_selection', 'pharma_reports']
```

## Modelos

| Modelo | Archivo | Propósito |
|---|---|---|
| `stock.scrap.batch` | `models/stock_scrap_batch.py` | Orden de baja múltiple |
| `scrap.history.legacy` | `models/scrap_history_legacy.py` | Registro histórico importado |
| `scrap.summary.2025` | `models/scrap_summary_2025.py` | Resumen anual consolidado |

## Estados del flujo

```
Borrador → Aprobación pendiente → Aprobado → Validado → Cancelado
```

- **Borrador**: El almacenista registra los productos y lotes a dar de baja
- **Aprobación pendiente**: Se notifica al gerente por correo
- **Aprobado**: El gerente confirma la baja
- **Validado**: Se ejecutan los movimientos de stock y se genera el PDF

## Reportes

| Archivo | Contenido |
|---|---|
| `report/stock_scrap_batch_report.xml` | PDF de la orden de baja |
| `report/scrap_history_legacy_report.xml` | PDF histórico de bajas |
| `report/scrap_summary_report.xml` | PDF de resumen anual |

## Seguridad

```
stock.scrap.batch.user    — Ver y crear bajas
stock.scrap.batch.manager — Aprobar y validar bajas
```

## Uso

1. Ir a **Inventario > Bajas > Nueva Baja Múltiple**
2. Agregar productos y lotes a dar de baja
3. Enviar a aprobación
4. El gerente aprueba o rechaza
5. Al aprobar, se generan los movimientos y el PDF

## Notas técnicas

- Requiere `lot_selection` para la selección de lotes con FEFO
- Los movimientos generados usan la ubicación "Pérdidas de inventario" configurada en el almacén
- El cron `scrap_batch_sequence.xml` mantiene la secuencia de folios

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: medicine_depot_scrap_batch]
