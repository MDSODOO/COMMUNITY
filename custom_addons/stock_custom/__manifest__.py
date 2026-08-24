# -*- coding: utf-8 -*-
{
    'name': 'Stock Custom (Compatibility Bridge)',
    'version': '19.0.99.0.0',
    'category': 'Tools',
    'author': 'Medicine Depot',
    'license': 'OPL-1',
    'summary': 'Legacy bridge that redirects to lot_selection',
    'description': """
Compatibility module kept to preserve the old technical name
`stock_custom` after the inventory lot search was moved into `lot_selection`.
""",
    'depends': [
        'lot_selection',
    ],
    'data': [
        'views/stock_move_line_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
