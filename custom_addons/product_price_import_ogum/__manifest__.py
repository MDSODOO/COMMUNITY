# -*- coding: utf-8 -*-
{
    'name': 'Importador de Precios de Venta OGUM',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Plantilla Excel para actualizar precios de venta de productos',
    'author': 'Daniel Cervera / QUIFAMESA',
    'website': 'https://quifamesa.mx',
    'license': 'LGPL-3',
    'depends': [
        'sales_team',
        'sale',
        'product',
        'mail',
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/product_sale_price_import_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
