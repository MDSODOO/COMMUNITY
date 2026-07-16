# -*- coding: utf-8 -*-
{
    'name': 'Custom Invoice Format — Medicine Depot',
    'version': '19.0.1.19.0',

    'category': 'Accounting/Accounting',
    'summary': 'Formato personalizado de factura cliente CFDI 4.0',
    'author': 'Medicine Depot - Daniel Cervera',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'md_cfdi_stamping',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/report_invoice.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'custom_invoice_format/static/src/css/report_invoice.css',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
