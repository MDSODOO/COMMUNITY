{
    'name': 'Quifamesa - Launcher Unificado (Command Palette + Apps Grid)',
    'summary': (
        'Paleta de comandos estilo Spotlight (Ctrl+K / Alt+Espacio) para '
        'buscar menús y productos con cantidad a la mano.'
    ),
    'version': '19.0.1.0.0',
    'category': 'Themes',
    'author': 'Quifamesa',
    'license': 'LGPL-3',
    # Fork de mds_raffle_campaign's sibling md_command_palette (Medicine
    # Depot), adaptado para Quifamesa: se quitan las dependencias de
    # medicine_depot_portal (rebrandea todo /my con su Bento-box) y
    # md_home_menu (hoy sin assets, no aporta nada) — ver homologación
    # documentada en las notas de este proyecto. tokens.scss reemplaza a
    # backend_tokens.scss como fuente de las custom properties --md-* que
    # consume launcher.scss.
    'depends': ['web', 'product'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'quifamesa_command_palette/static/src/scss/tokens.scss',
            'quifamesa_command_palette/static/src/scss/launcher.scss',
            'quifamesa_command_palette/static/src/js/launcher.js',
            'quifamesa_command_palette/static/src/xml/launcher.xml',
        ],
    },
    'installable': True,
    'application': False,
}
