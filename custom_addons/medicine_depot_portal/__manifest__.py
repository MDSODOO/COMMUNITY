# -*- coding: utf-8 -*-
{
    'name': 'Medicine Depot - Portal Bento',
    'version': '19.0.2.10.10',
    'category': 'Website/Portal',
    'summary': (
        "Rediseño Bento-box del Portal del Cliente (/my) con CSS Grid "
        "y Glassmorphism. Stock siempre etiquetado como 'A la mano'."
    ),
    'description': """
Reemplaza la vista portal.portal_my_home por un layout Bento-box
(CSS Grid + Glassmorphism) que muestra dinámicamente:
  * Pedido activo del cliente
  * Facturas pendientes (conteo y total residual)
  * Productos favoritos (top más comprados, con stock 'A la mano')
  * Bitácora reciente del usuario logueado

Regla terminológica estricta: la existencia física de inventario se
nombra siempre 'A la mano' — nunca 'Disponible'.
    """,
    'author': 'Daniel-Cervera',
    'website': 'https://medicinedepot.example',
    'license': 'LGPL-3',
    'depends': [
        'portal',
        'mail',
        'sale_management',
        'account',
        'stock',
        'website',
        'website_sale',
        'auth_signup',
        'web_tour',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/auth_signup_config.xml',
        'data/website_domain_config.xml',
        'data/pharmacovigilance_sequence.xml',
        'data/affiliation_rate_limit_cron.xml',
        'views/snippets/s_md_hero_bento.xml',
        'views/snippets/s_md_audit_grid.xml',
        'views/snippets/s_md_service_grid.xml',
        'views/snippets/s_md_blog_grid.xml',
        'views/snippets/s_md_branches.xml',
        'views/snippets/s_md_two_col.xml',
        'views/snippets/s_md_wizard_hero.xml',
        'views/snippets/s_md_product_card.xml',
        'views/snippets/s_md_logos_ticker.xml',
        'views/public_templates.xml',
        'views/auth_templates.xml',
        'views/portal_templates.xml',
        'views/afiliacion_templates.xml',
        'views/pharmacovigilance_views.xml',
        'data/website_pages.xml',
        'views/public_pages_inherit.xml',
        'views/shop_session_inherits.xml',
        'data/website_menu.xml',
        'views/manual_tour.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'medicine_depot_portal/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            # ORDEN CRITICO: _tokens.scss debe ir primero porque define
            # variables/mixins usados por los siguientes SCSS del bundle.
            'medicine_depot_portal/static/src/scss/_tokens.scss',
            'medicine_depot_portal/static/src/scss/login_custom.scss',
            'medicine_depot_portal/static/src/scss/public_bento.scss',
            'medicine_depot_portal/static/src/scss/portal_bento.scss',
            'medicine_depot_portal/static/src/scss/afiliacion.scss',
            'medicine_depot_portal/static/src/scss/snippets/_s_cover.scss',
            'medicine_depot_portal/static/src/scss/snippets/_s_features.scss',
            'medicine_depot_portal/static/src/scss/snippets/_s_image_text.scss',
            'medicine_depot_portal/static/src/scss/snippets/_s_branches.scss',
            'medicine_depot_portal/static/src/scss/snippets/_s_blog_grid.scss',
            'medicine_depot_portal/static/src/js/md_wizard_base.js',
            'medicine_depot_portal/static/src/js/public_navbar.js',
            'medicine_depot_portal/static/src/js/public_surface_bridge.js',
            'medicine_depot_portal/static/src/js/login_glass_island.js',
            'medicine_depot_portal/static/src/js/portal_bento.js',
            'medicine_depot_portal/static/src/js/portal_home_counters_patch.js',
            'medicine_depot_portal/static/src/js/md_toast_promoter.js',
            'medicine_depot_portal/static/src/js/shop_drawer.js',
            'medicine_depot_portal/static/src/js/shop_ux.js',
            'medicine_depot_portal/static/src/js/snippets/s_md_gmap.js',
            'medicine_depot_portal/static/src/js/afiliacion.js',
            'medicine_depot_portal/static/src/js/pharmacovigilance.js',
            'medicine_depot_portal/static/src/js/public_animations.js',
            'medicine_depot_portal/static/src/js/public_branches_geo.js',
            'medicine_depot_portal/static/src/js/tours/md_afiliacion_tour.js',
            'medicine_depot_portal/static/src/js/tours/md_portal_dashboard_tour.js',
            'medicine_depot_portal/static/src/js/tours/md_shop_ala_mano_tour.js',
        ],
        'web.assets_backend': [
            # backend_tokens.scss debe ir PRIMERO: define las CSS custom
            # properties (--md-*) que backend_bento.scss consume.
            'medicine_depot_portal/static/src/scss/backend_tokens.scss',
            'medicine_depot_portal/static/src/scss/backend_bento.scss',
            # backend_dark.scss va AL FINAL: sus reglas (gateadas por
            # html.o_md_dark_mode/[data-bs-theme]) deben cargar despues de
            # backend_bento.scss para ganar en empate de especificidad.
            # Migrado desde web.assets_web_dark (2026-07-27) -- ese bundle
            # nunca carga en Odoo 19 Community, ver cabecera del archivo.
            'medicine_depot_portal/static/src/scss/backend_dark.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
