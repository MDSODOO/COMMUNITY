# sale_account_custom — v19.0.0.9

**Categoría**: Tools | **Licencia**: LGPL-3

## Propósito

Módulo de permisos y reglas de negocio para ventas y facturas en el contexto mexicano de Medicine Depot:

- Permisos granulares: qué grupos pueden editar campos sensibles en facturas y órdenes de venta
- Lógica de **posición fiscal para zona fronteriza** (IVA reducido en regiones fronterizas México)
- Acción de servidor para automatizaciones de aprobación

## Dependencias

```python
depends = ['sale', 'account', 'mail', 'l10n_mx_edi']
```

## Modelos

| Modelo | Archivo | Propósito |
|---|---|---|
| `account.move` | `models/account_move.py` | Restricciones de edición por grupo |
| `sale.order` | `models/sale_order.py` | Restricciones de edición por grupo |
| `account.fiscal.position` | `models/account_fiscal_position.py` | Lógica de zona fronteriza |
| `ir.actions.server` | `models/ir_actions_server.py` | Acciones de servidor para aprobaciones |

## Seguridad

```
security/security.xml — Grupos: sale_custom.group_invoice_editor, sale_custom.group_zone_manager
```

## Vistas

- `views/account_move_views.xml` — Campos adicionales y restricciones en facturas
- `views/sale_order_views.xml` — Campos adicionales en órdenes de venta

## Tests

```bash
pytest sale_account_custom/tests/test_fiscal_position_border_zone.py -v
```

## Reglas de zona fronteriza

Los clientes con dirección en municipios fronterizos (lista configurable) reciben automáticamente la posición fiscal de IVA reducido al confirmar la orden. La lógica está en `account_fiscal_position.py`.

## Notas técnicas

- Versión 0.9: aún sin llegar a v1.0 — algunas reglas de negocio están pendientes de formalizar
- Las migraciones (v0.2 → v0.9) corrigen datos de posición fiscal en órdenes históricas

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: sale_account_custom]
