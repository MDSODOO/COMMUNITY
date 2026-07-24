{
    'name': 'Medicine Depot - Gestión de Lotes',
    'version': '19.0.1.20.0',
    'category': 'Inventory',
    'license': 'LGPL-3',
    'author': 'Medicine Depot',
    'website': 'https://medicinedepot.mx',
    'summary': 'Personalización de lotes/números de serie con mejora de UI',
    'description': '''
    Módulo que migra personalizaciones de Odoo Studio en el modelo stock.lot
    a código puro, preservando datos históricos e mejorando la experiencia de usuario.

    Características:
    - Herencia limpia del modelo stock.lot
    - Vistas refactorizadas sin artefactos de Studio
    - Campos personalizados con validaciones nativas
    - Mejor rendimiento y mantenibilidad
    - Compatibilidad total con datos existentes
    ''',
    'depends': [
        'stock',
        'purchase',
        'purchase_stock',
        'product_expiry',
        'mail',
        'base',
        'medicine_depot_portal',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/server_actions.xml',
        'views/lot_a_la_mano_wizard_views.xml',
        'views/production_lot_views.xml',
        'views/production_lot_handheld_views.xml',
        'views/production_lot_forms.xml',
        'views/production_lot_company_views.xml',
        'views/product_template_on_hand_button_views.xml',
        'views/res_partner_hide_lot_button.xml',
        'views/product_template_kanban_card_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # medicine_depot_portal (dependencia) ya inyecta backend_tokens.scss
            # + backend_bento.scss antes que esto en el mismo bundle, asi que
            # las custom properties --md-* estan disponibles sin @import.
            'md_lots_management/static/src/scss/handheld_kanban.scss',
            'md_lots_management/static/src/js/handheld_kanban_view.js',
            'md_lots_management/static/src/scss/product_kanban_card.scss',
            'md_lots_management/static/src/scss/production_lot_kanban.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'external_dependencies': {
        'python': [],
    },
}
