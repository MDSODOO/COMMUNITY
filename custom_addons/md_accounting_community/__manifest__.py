# -*- coding: utf-8 -*-
{
    "name": "MDS - Contabilidad Community (menú unificado)",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Menú superior unificado estilo Enterprise sobre módulos OCA de contabilidad",
    "description": """
Módulo glue de solo menús. No define modelos ni lógica de negocio propia:
reorganiza acciones que ya existen en `account`, `analytic`, `fleet`,
`account_asset_management`, `account_reconcile_oca`,
`account_journal_lock_date`, `account_financial_report` y
`account_tax_balance` bajo la jerarquía visual de Odoo Enterprise
(Transacciones / Activos y Pasivos / Bloqueo / Revisión y Reportes).

Incluye además un primer reporte de Balance General y P&L (MIS Builder)
sobre el agrupador SAT (1 Activo / 2 Pasivo / 3 Capital / 4 Ingresos /
5 Costos / 6 Gastos). DIOT y Contabilidad Electrónica XML (SAT) siguen sin
módulo instalado. Ver docs/plans/PLAN_ADAPTACION_CONTABILIDAD_COMMUNITY.md.
    """,
    "author": "Medicine Depot",
    "license": "LGPL-3",
    "depends": [
        "account",
        "analytic",
        "fleet",
        "account_asset_management",
        "account_reconcile_oca",
        "account_journal_lock_date",
        "account_financial_report",
        "account_tax_balance",
        "mis_builder",
    ],
    "data": [
        "data/mis_report_balance_pyg.xml",
        "data/mis_report_instance_balance_pyg.xml",
        "views/md_accounting_menus.xml",
    ],
    "installable": True,
}
