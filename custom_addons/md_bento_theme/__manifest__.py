# -*- coding: utf-8 -*-
{
    'name': 'Medicine Depot - Bento Theme',
    'version': '19.0.1.0.14',
    'category': 'Website/Theme',
    'summary': 'Bento and glassmorphism theme for Medicine Depot eCommerce.',
    'author': 'Medicine Depot',
    'website': 'https://medicinedepot.com.mx',
    'license': 'LGPL-3',
    # Requires manual activation as the website theme in Odoo.
    # It must replace theme_bewise on the target website; only one theme can
    # own the final storefront visual layer at a time.
    # Install order: medicine_depot_portal -> custom_shop_qty_selector ->
    # portal_picking_visibility -> md_bento_theme.
    # Depende de md_dark_mode para que el orden de carga de assets sea
    # determinista: sus overrides de html.o_md_dark_mode deben cargar antes
    # que la nueva capa de backend de este modulo (ver
    # docs/audits/2026-07-23_backend_redesign_action_plan.md en el repo).
    'depends': [
        'website',
        'website_sale',
        'medicine_depot_portal',
        'custom_shop_qty_selector',
        'md_dark_mode',
    ],
    'data': [
        'views/layout.xml',
        'views/snippets/s_socios.xml',
        'views/homepage.xml',
        'views/shop_templates.xml',
        'views/product_templates.xml',
        'views/cart_templates.xml',
        'views/affiliate_templates.xml',
        'views/snippets.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'md_bento_theme/static/src/xml/switch_company_menu.xml',
            # Depende de md_dark_mode (ver 'depends' arriba) para que sus
            # overrides de html.o_md_dark_mode carguen primero; esta capa
            # solo anade transiciones/hover, nunca redefine lo que ese
            # modulo ya gestiona en modo oscuro.
            'md_bento_theme/static/src/scss/backend/md_backend_glass.scss',
        ],
        'web.assets_frontend': [
            'md_bento_theme/static/src/scss/md_tokens.scss',
            'medicine_depot_portal/static/src/scss/_tokens.scss',
            'md_bento_theme/static/src/scss/site_unify.scss',
            'md_bento_theme/static/src/scss/md_layout.scss',
            'md_bento_theme/static/src/scss/md_bento.scss',
            'md_bento_theme/static/src/scss/snippets/_s_socios.scss',
            'md_bento_theme/static/src/scss/md_shop.scss',
            'md_bento_theme/static/src/scss/md_cart.scss',
            'md_bento_theme/static/src/scss/md_dark.scss',
            'md_bento_theme/static/src/js/md_bento_interactions.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
