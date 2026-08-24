# -*- coding: utf-8 -*-
{
    'name': 'Medicine Depot - Login Personalizado',
    'version': '19.0.1.0.0',
    'category': 'Website/Portal',
    'summary': (
        "Rediseño Glassmorphism de /web/login y /web/signup con branding "
        "Medicine Depot (teal/verde) y panel CTA de registro."
    ),
    'description': """
Extraído de medicine_depot_portal (2026-08-17) para aislar la
personalización del login en un módulo independiente, evitando que
coincida/colisione con la de otros proyectos (ver quifamesa_web_login)
que comparten el mismo addons_path.

Depende de medicine_depot_portal solo para reutilizar los design tokens
de marca (_tokens.scss) — no toca ninguna de sus otras vistas.
    """,
    'author': 'Daniel-Cervera',
    'website': 'https://medicinedepot.example',
    'license': 'LGPL-3',
    'depends': [
        'web',
        'website',
        'auth_signup',
        'medicine_depot_portal',
    ],
    'data': [
        'views/auth_templates.xml',
        'views/login_layout_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'md_web_login/static/src/scss/login_custom.scss',
            'md_web_login/static/src/js/login_glass_island.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
