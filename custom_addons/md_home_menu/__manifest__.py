{
    'name': 'MDS - Selector de Aplicaciones (Grid)',
    'summary': 'Reemplaza el listado de texto del menu de apps por una cuadricula de iconos, como en Odoo Enterprise/odoo.sh.',
    'version': '19.0.1.0.0',
    'category': 'Hidden',
    'author': 'MedicineDepot Sureste',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [],
    # Assets deliberadamente vacios desde la fusion con md_command_palette
    # (ver MENU_UX_AUDIT_AND_PLAN.md): home_menu.xml/scss quedaban activos en
    # paralelo al nuevo MdLauncher, generando un <Dropdown> nativo "fantasma"
    # (estilizado con la paleta de colores vieja, sin buscador) que solo
    # dejaba de verse porque un listener JS de otro modulo le robaba el
    # click. Ese Dropdown nativo intacto sigue siendo la red de seguridad si
    # JS falla en cargar, pero ya no carga la version con grid de iconos de
    # marca propia — evita mantener dos sistemas visuales redundantes.
    # Los archivos home_menu.xml/home_menu.scss se conservan en el modulo
    # (no se borran) por si se decide revertir este cambio.
    'assets': {},
    'installable': True,
    'application': False,
}
