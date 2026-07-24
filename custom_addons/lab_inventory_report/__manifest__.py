# -*- coding: utf-8 -*-
{
    'name': 'Reporte: Laboratorios a la mano',
    'version': '19.0.1.1.0',
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

Migrado en 19.0.1.1.0 de la relación Studio x_line (0% de productos
poblados, bug de nombre de columna que dejaba la vista SQL siempre vacía)
a md.product.line / product_line_id (módulo md_product_lines, ~97% de
productos poblados).
    """,
    'depends': [
        'product',
        'stock',
        'pharma_reports',
        'md_product_lines',
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
