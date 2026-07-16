{
    'name': 'Medicine Depot - CFDI 4.0 (Community)',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Generación, sellado y timbrado de CFDI 4.0 sin depender de l10n_mx_edi (Enterprise)',
    'description': '''
        Genera y sella CFDI 4.0 usando la librería satcfdi (MIT) y timbra
        contra un PAC directo (Finkok / SW Sapien), como reemplazo Community
        del módulo Enterprise l10n_mx_edi.
    ''',
    'author': 'Daniel Cervera',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'l10n_mx',
        'point_of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        'views/account_move_views.xml',
        'views/pos_session_views.xml',
    ],
    'external_dependencies': {
        'python': ['satcfdi'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
