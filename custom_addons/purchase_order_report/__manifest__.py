# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Report (Compatibility Bridge)',
    'version': '19.0.99.0.0',
    'category': 'Reporting',
    'author': 'Medicine Depot',
    'license': 'LGPL-3',
    'summary': 'Legacy bridge that redirects to pharma_reports',
    'description': """
Compatibility module kept to preserve the old technical name
`purchase_order_report` after the merge into `pharma_reports`.
""",
    'depends': [
        'pharma_reports',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
