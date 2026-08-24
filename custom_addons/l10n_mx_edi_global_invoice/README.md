# l10n_mx_edi_global_invoice — v19.0.0.2

**Categoría**: Tools | **Licencia**: LGPL-3

## Propósito

Generación de Facturas Globales CFDI 4.0 desde órdenes del POS, según las reglas del SAT mexicano. Una factura global agrupa múltiples órdenes de POS de consumidores finales (RFC genérico XAXX010101000) en un único CFDI.

## Dependencias

```python
depends = ['account', 'l10n_mx_edi', 'point_of_sale', 'sale']
```

## Modelos

| Modelo | Propósito |
|---|---|
| `account.move` | Extensión para marcar/generar facturas globales |
| `pos.session` | Hook para accionar facturación global al cerrar sesión |
| `pos.config` | Configuración: habilitar factura global por terminal |
| `res.config.settings` | Configuración global del módulo |
| `pos.order` | Marcado de órdenes incluidas en factura global |
| `l10n_mx_edi.document` | Extensión para complemento CFDI |

## Wizards

| Wizard | Propósito |
|---|---|
| `pos.order.make.invoice` | Generar factura global desde sesión POS |
| `sale.order.make.invoice` | Generar factura global desde órdenes de venta |

## Vistas

- `views/account_move_views.xml` — Botón y panel en facturas
- `views/res_config_settings.xml` — Configuración del módulo
- `views/pos_order_views.xml` — Vista de órdenes POS con estado de facturación

## Configuración

1. Ir a **Configuración > Punto de Venta**
2. Activar "Factura Global CFDI 4.0"
3. Configurar periodo de agrupación (diario/semanal/mensual)
4. El cron `cron_global_invoice` ejecuta la generación automáticamente

## Notas técnicas

- Oculta la acción nativa de factura global de Odoo (`data/hide_native_global_invoice_action.xml`)
- Versión 0.2 — módulo en maduración, sin migraciones formales aún
- Compatible con `l10n_mx_edi` v4.0 únicamente

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: l10n_mx_edi_global_invoice]
