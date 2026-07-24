# -*- coding: utf-8 -*-
{
    'name': 'Sale Lot Report (Compatibility Bridge)',
    'version': '19.0.99.0.0',
    'category': 'Reporting',
    'author': 'Medicine Depot',
    'license': 'OPL-1',
    'summary': 'Legacy bridge that redirects to pharma_reports',
    'description': """
Compatibility module kept to preserve the old technical name
`sale_lot_report` after the merge into `pharma_reports`.
""",
    'depends': [
        'pharma_reports',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
