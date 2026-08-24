# -*- coding: utf-8 -*-
{
    "name": "MDS - Contabilidad Community (integración a Facturación)",
    "version": "19.0.2.0.0",
    "category": "Accounting/Accounting",
    "summary": "Completa el menú nativo de Facturación para igualar Enterprise",
    "description": """
Módulo glue de solo menús. No define modelos ni lógica de negocio propia:
la mayoría de los items del menú Enterprise (Asientos, Apuntes analíticos,
Conciliar, Libro Mayor/Diario, Balanza, Partidas Abiertas, Antigüedad,
VAT, Activos) ya los agrega cada módulo OCA de forma nativa dentro de
Facturación (`account.menu_finance`) — este módulo solo agrega lo que
realmente faltaba (Transferencias, Flotilla, Declaración fiscal, Fechas
de bloqueo, Balance General y P&L) y reordena/renombra lo existente para
igualar la agrupación visual real de Enterprise (Contabilidad >
Transacciones / Activos y pasivos / Bloqueando; Revisión; Reportes).

Incluye un primer reporte de Balance General y P&L (MIS Builder) sobre el
agrupador SAT (1 Activo / 2 Pasivo / 3 Capital / 4 Ingresos / 5 Costos /
6 Gastos). "Préstamos" y DIOT/Contabilidad Electrónica XML (SAT) siguen
sin módulo instalado. Ver
docs/plans/PLAN_ADAPTACION_CONTABILIDAD_COMMUNITY.md.
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
