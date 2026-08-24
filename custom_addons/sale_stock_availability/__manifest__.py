{
    'name': 'Sale Stock Availability Enforcement',
    'version': '19.0.3.2.0',
    'category': 'Sales/Sales',
    'summary': 'Restringe el catálogo de ventas a productos con existencia a la mano y limita cantidades',
    'author': 'Medicine Depot - Daniel Cervera',
    'license': 'LGPL-3',
    'depends': ['sale_stock', 'stock', 'product', 'bus'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_stock_availability/static/src/js/clamp_dialog_service.js',
            'sale_stock_availability/static/src/js/product_catalog_patch.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
