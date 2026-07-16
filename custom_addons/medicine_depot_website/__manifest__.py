# -*- coding: utf-8 -*-
{
    'name': 'Medicine Depot - Website',
    'version': '19.0.1.4.3',
    'category': 'Website',
    'summary': 'Sitio web público: homepage bento, afiliación CRM, MedicD, sucursales',
    'description': 'Módulo de website público para Medicine Depot: homepage Bento-box, formulario de afiliación profesional, programa MedicD, mapa de sucursales con pines SVG animados.',
    'author': 'Daniel-Cervera',
    'website': 'https://medicinedepot.com.mx',
    'license': 'LGPL-3',
    'depends': [
        'medicine_depot_portal',  # bento shell, rutas base, tokens SCSS
        'custom_shop_qty_selector',# control de cantidad y filtros personalizados de la tienda
        'crm',                    # crm.lead para afiliacion + medicd
    ],
    'data': [
        # Snippets (antes de páginas que los llaman)
        'views/snippets/s_md_hero.xml',
        'views/snippets/s_md_bento_grid.xml',
        'views/snippets/s_md_socios.xml',
        'views/snippets/s_md_podcast.xml',
        # Páginas (extienden templates de medicine_depot_portal)
        'views/pages/medicd.xml',
        'views/pages/homepage.xml',
        'views/pages/product_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # SCSS se compilan en scope de _tokens.scss del portal
            'medicine_depot_website/static/src/scss/snippets/_s_hero.scss',
            'medicine_depot_website/static/src/scss/snippets/_s_socios.scss',
            'medicine_depot_website/static/src/scss/medicine_depot_website.scss',
            # JS publicWidget (NO OWL)
            'medicine_depot_website/static/src/js/snippets/s_md_hero.js',
            'medicine_depot_website/static/src/js/snippets/s_md_sucursales.js',
            'medicine_depot_website/static/src/js/medicd.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
