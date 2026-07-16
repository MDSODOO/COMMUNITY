# -*- coding: utf-8 -*-
{
    'name': 'Purchase Lot Selection (Compatibility Bridge)',
    'version': '19.0.99.0.0',
    'category': 'Tools',
    'author': 'Medicine Depot',
    'license': 'OPL-1',
    'summary': 'Legacy bridge that redirects to lot_selection',
    'description': """
Compatibility module kept to preserve the old technical name
`purchase_lot_selection` after the merge into `lot_selection`.
""",
    'depends': [
        'lot_selection',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
