# -*- coding: utf-8 -*-
{
    'name': 'Medicine Depot Scrap Batch',
    'version': '19.0.1.2.3',
    'category': 'Inventory/Inventory',
    'author': 'Medicine Depot',
    'license': 'OPL-1',
    'summary': 'Órdenes de bajas múltiple con validación por gerente',
    'depends': ['stock', 'product_expiry', 'purchase', 'lot_selection', 'pharma_reports'],
    'data': [
        'security/ir.model.access.csv',
        'security/security_rules.xml',
        'data/scrap_summary_xmlid_cleanup.xml',
        'data/scrap_batch_sequence.xml',
        'report/stock_scrap_batch_report.xml',
        'report/scrap_history_legacy_report.xml',
        'report/scrap_summary_report.xml',
        'report/scrap_batch_consolidated_report.xml',
        'report/scrap_batch_paperformat.xml',
        'views/stock_scrap_batch_views.xml',
        'views/scrap_history_legacy_views.xml',
        'views/scrap_summary_2025_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # variables.scss es importado por dashboard.scss — no registrar directamente
            'medicine_depot_scrap_batch/static/src/scss/dashboard.scss',
        ],
        'web.assets_web_dark': [
            # Se carga SOLO en modo oscuro — sin selectores adicionales requeridos
            'medicine_depot_scrap_batch/static/src/scss/dashboard_dark.scss',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
