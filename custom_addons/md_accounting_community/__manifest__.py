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

Balance General, Pérdidas y Ganancias, DIOT y Contabilidad Electrónica XML
(SAT) NO están aquí todavía: no existe ningún módulo instalado que los
provea. Ver docs/plans/PLAN_ADAPTACION_CONTABILIDAD_COMMUNITY.md.
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
    ],
    "data": [
        "views/md_accounting_menus.xml",
    ],
    "installable": True,
}
