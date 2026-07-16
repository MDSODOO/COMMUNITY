{
    'name': 'MDS - Cliente de Correo',
    'summary': 'Bandeja de correo estilo Gmail sobre mail.mail (sin depender de web_enterprise).',
    'version': '19.0.1.0.0',
    'category': 'Discuss',
    'author': 'MedicineDepot Sureste',
    'license': 'LGPL-3',
    'depends': ['mail', 'web'],
    'data': [
        'views/mail_client_action.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'md_mail_client/static/src/scss/mail_client.scss',
            'md_mail_client/static/src/js/mail_client.js',
            'md_mail_client/static/src/xml/mail_client.xml',
        ],
    },
    'installable': True,
    'application': False,
}
