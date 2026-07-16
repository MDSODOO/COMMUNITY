{
    'name': 'MDS - Historial Legacy de Punto de Venta',
    'summary': 'Archivo de solo lectura de los pedidos de PoS del sistema Microsip anterior (2021-2025), para consulta/reportes sin recrear pos.session historicas. / Read-only archive of legacy Microsip PoS orders (2021-2025), for lookup/reporting without recreating historical pos.sessions.',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'author': 'MedicineDepot Sureste',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/legacy_pos_order_views.xml',
        'views/pos_order_unified_views.xml',
    ],
    'installable': True,
    'application': False,
}
