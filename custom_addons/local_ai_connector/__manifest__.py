{
    'name': 'MDS - Conector de IA Local',
    'summary': 'Copiloto interno (Ollama, en el host) para consultas de inventario y cotizaciones por imagen.',
    'version': '19.0.1.1.0',
    'category': 'Tools',
    'author': 'MedicineDepot Sureste',
    'license': 'LGPL-3',
    # requests ya viene con la imagen odoo:19.0, se declara para que quede
    # explicito -- no es un paquete que este modulo instale. Pillow (PIL)
    # tambien ya viene incluido (lo usa el propio Odoo para imagenes).
    'external_dependencies': {
        'python': ['requests', 'PIL'],
    },
    'depends': ['stock', 'product', 'sale', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/image_quote_sequence.xml',
        'data/image_quote_cron.xml',
        'views/image_quote_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'local_ai_connector/static/src/scss/image_quote_drop_dialog.scss',
            'local_ai_connector/static/src/js/ai_inventory_query_dialog.js',
            'local_ai_connector/static/src/js/ai_inventory_query_systray.js',
            'local_ai_connector/static/src/js/image_quote_drop_dialog.js',
            # launcher_quick_actions.js importa los 2 dialogos de arriba --
            # debe cargar despues de ambos en el bundle.
            'local_ai_connector/static/src/js/launcher_quick_actions.js',
            'local_ai_connector/static/src/xml/ai_inventory_query.xml',
            'local_ai_connector/static/src/xml/image_quote_drop_dialog.xml',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
}
