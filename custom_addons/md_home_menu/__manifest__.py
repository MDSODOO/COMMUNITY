{
    'name': 'MDS - Selector de Aplicaciones (Grid)',
    'summary': 'Reemplaza el listado de texto del menu de apps por una cuadricula de iconos, como en Odoo Enterprise/odoo.sh.',
    'version': '19.0.1.0.0',
    'category': 'Hidden',
    'author': 'MedicineDepot Sureste',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'md_home_menu/static/src/scss/home_menu.scss',
            'md_home_menu/static/src/xml/home_menu.xml',
        ],
    },
    'installable': True,
    'application': False,
}
