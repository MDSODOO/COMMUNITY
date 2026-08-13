{
    'name': 'MDS - Campañas de Rifa (Folios y Sorteo)',
    'summary': (
        'Motor de reglas para generación de folios de rifa a partir de '
        'ventas físicas (POS) y B2B online, con ruleta de sorteo visual.'
    ),
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'author': 'MedicineDepot Sureste',
    'website': 'https://medicinedepot.com.mx',
    'license': 'LGPL-3',
    'depends': ['sale', 'point_of_sale', 'mail', 'md_product_lines', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'views/raffle_ticket_views.xml',
        'views/raffle_ticket_summary_views.xml',
        'views/raffle_rule_views.xml',
        'views/raffle_campaign_views.xml',
        'views/res_config_settings_views.xml',
        'views/raffle_menus.xml',
        'data/raffle_whatsapp_cron.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mds_raffle_campaign/static/src/js/raffle_wheel.js',
            'mds_raffle_campaign/static/src/scss/raffle_wheel.scss',
            'mds_raffle_campaign/static/src/xml/raffle_wheel.xml',
        ],
    },
    'installable': True,
    'application': True,
}
