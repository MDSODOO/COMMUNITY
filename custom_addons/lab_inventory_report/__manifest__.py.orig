# -*- coding: utf-8 -*-
{
    'name': 'Reporte: Laboratorios a la mano',
    'version': '19.0.1.0.2',
    'category': 'Inventory/Reporting',
    'author': 'Medicine Depot, Daniel Cervera',
    'license': 'OPL-1',
    'summary': 'Reporte mensual A la mano por laboratorio y sucursal',
    'description': """
Desglose A la mano para los laboratorios:
  SERRAL, PERRIGO - QUIFA, GELCAPS/PHARMACAPS, RAAM.

Distribuido por las 6 sucursales operativas. Incluye:
  - Vista lista y pivot agrupada por laboratorio, producto y sucursal.
  - Acción planificada mensual (último día del mes) para generar el concentrado.
    """,
    'depends': [
        'product',
        'stock',
        'pharma_reports',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/report_lab_inventory_templates.xml',
        'views/report_lab_inventory_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
