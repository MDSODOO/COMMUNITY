{
    'name': 'MDS - Modo Oscuro',
    'summary': 'Toggle de modo oscuro para el backend, con CSS propio (sin depender de web_enterprise).',
    'version': '19.0.2.1.0',
    'category': 'Themes',
    'author': 'MedicineDepot Sureste',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'md_dark_mode/static/src/scss/dark_mode.scss',
            'md_dark_mode/static/src/js/dark_mode_toggle.js',
            'md_dark_mode/static/src/xml/dark_mode_toggle.xml',
        ],
    },
    'installable': True,
    'application': False,
}
