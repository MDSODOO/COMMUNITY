{
    'name': 'MDS - Launcher Unificado (Command Palette + Apps Grid)',
    'summary': (
        'Paleta de comandos estilo Spotlight (Ctrl+K / Alt+Espacio / click en '
        'el boton de Apps) para buscar menus, productos con cantidad a la '
        'mano, y lanzar apps instaladas desde "Acciones Sugeridas".'
    ),
    'version': '19.0.2.0.0',
    'category': 'Themes',
    'author': 'MedicineDepot Sureste',
    'license': 'LGPL-3',
    # 'medicine_depot_portal' agregado a proposito: garantiza que
    # backend_tokens.scss (--md-*) cargue ANTES que launcher.scss dentro del
    # mismo bundle web.assets_backend. Sin esta dependencia explicita, el
    # orden entre modulos sin relacion de dependencia no esta garantizado.
    # 'md_home_menu' agregado tras la auditoria de integracion
    # (MENU_UX_AUDIT_AND_PLAN.md): este modulo intercepta por JS el click de
    # ".o_navbar_apps_menu", que md_home_menu modifica via t-inherit de
    # web.NavBar.AppsMenu. La dependencia formaliza ese acoplamiento (antes
    # implicito) y garantiza orden de carga determinista entre ambos.
    'depends': ['web', 'product', 'medicine_depot_portal', 'md_home_menu'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'md_command_palette/static/src/scss/launcher.scss',
            'md_command_palette/static/src/js/launcher.js',
            'md_command_palette/static/src/xml/launcher.xml',
        ],
    },
    'installable': True,
    'application': False,
}
