# -*- coding: utf-8 -*-
{
    'name': 'Purchase — Propagación de Referencia de Proveedor',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': (
        'Propaga partner_ref de la OC a ref y payment_reference '
        'en la factura de proveedor al crearla.'
    ),
    'author': 'Medicine Depot - Daniel Cervera',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
