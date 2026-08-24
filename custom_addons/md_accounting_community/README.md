# md_accounting_community

Módulo glue de solo menús. Reorganiza acciones ya provistas por `account`,
`analytic`, `fleet`, `account_asset_management`, `account_reconcile_oca`,
`account_journal_lock_date`, `account_financial_report` y
`account_tax_balance` bajo un menú superior "Contabilidad Community" con la
jerarquía visual de Odoo Enterprise:

- **Transacciones**: Asientos, Transferencias, Apuntes analíticos.
- **Activos y Pasivos**: Activos fijos, Flotilla.
- **Bloqueo**: Conciliación bancaria, Declaraciones fiscales (IVA), Fechas de bloqueo.
- **Revisión y Reportes**: Balanza de Comprobación, Libro Mayor, Libro Diario,
  Partidas Abiertas, Antigüedad de Saldos, Informe de Impuestos (VAT).

No define modelos, vistas de formulario ni lógica de negocio propia — solo
`ir.ui.menu`. La seguridad la siguen imponiendo los modelos/acciones
originales; el menú raíz solo se limita a los grupos de Contabilidad.

## Pendiente (no incluido a propósito)

Balance General, Pérdidas y Ganancias, DIOT y Contabilidad Electrónica XML
(SAT) no tienen módulo instalado que los provea todavía. Ver
`docs/plans/PLAN_ADAPTACION_CONTABILIDAD_COMMUNITY.md` en el repo principal
de Medicine Depot para el gap analysis completo.
