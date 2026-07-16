# -*- coding: utf-8 -*-
{
    'name': 'Permisos en ventas y facturas',
    'version': '19.0.0.10',
    'category': 'Tools',
    'author': 'INFLEXYON',
    'license': 'OPL-1',
    'summary': 'Permisos en ventas y facturas',
    'description': """Permisos en ventas y facturas""",

    'depends': [
        'sale',
        'account',
        'mail',
        'md_cfdi_stamping',
    ],
    "data": [
        'security/security.xml',
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'website': 'https://www.inflexyon.mx',
}
