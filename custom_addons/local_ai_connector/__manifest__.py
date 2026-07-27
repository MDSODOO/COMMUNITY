{
    'name': 'MDS - Conector de IA Local',
    'summary': 'Copiloto interno (Ollama, en el host) para consultas de inventario en lenguaje natural.',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'author': 'MedicineDepot Sureste',
    'license': 'LGPL-3',
    # requests ya viene con la imagen odoo:19.0, se declara para que quede
    # explicito -- no es un paquete que este modulo instale.
    'external_dependencies': {
        'python': ['requests'],
    },
    'depends': ['stock', 'product'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'local_ai_connector/static/src/js/ai_inventory_query_dialog.js',
            'local_ai_connector/static/src/js/ai_inventory_query_systray.js',
            'local_ai_connector/static/src/xml/ai_inventory_query.xml',
        ],
    },
    'installable': True,
    'application': False,
}
