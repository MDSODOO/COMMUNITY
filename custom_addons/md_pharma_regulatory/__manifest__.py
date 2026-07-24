{
    'name': 'Medicine Depot - Homologación Regulatoria COFEPRIS',
    'version': '19.0.9.12.0',
    'category': 'Inventory',
    'summary': 'Campos regulatorios COFEPRIS y categorización de productos por sustancia activa',
    'description': '''
        Agrega campos de homologación regulatoria (sustancia activa, concentración,
        registro sanitario, requiere receta, controlado) al catálogo de productos,
        un modelo de Sustancia Activa para agrupar/buscar equivalentes
        terapéuticos entre marcas y presentaciones distintas, y una cola de
        revisión manual para candidatos encontrados por el buscador PLM
        (nunca se escribe al producto sin aprobación humana).
    ''',
    'author': 'Daniel Cervera',
    'license': 'LGPL-3',
    # 'medicine_depot_portal' agregado a proposito: garantiza que
    # backend_tokens.scss (--md-*) cargue ANTES que
    # product_kanban_pos_style.scss dentro del mismo bundle
    # web.assets_backend (mismo criterio que md_command_palette).
    'depends': ['product', 'stock', 'medicine_depot_portal'],
    'data': [
        'security/ir.model.access.csv',
        'views/active_substance_views.xml',
        'views/abbreviation_views.xml',
        'views/product_template_views.xml',
        'views/product_visual_views.xml',
        'views/regulatory_review_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'md_pharma_regulatory/static/src/scss/product_kanban_pos_style.scss',
            # MdKanbanLotDetailPopup: réplica del LotDetailPopup del POS (rama
            # de lotes/FEFO) para el Kanban de Inventario. utils antes que el
            # componente que los importa; botón widget al final (importa el
            # popup para abrirlo on-click).
            'md_pharma_regulatory/static/src/kanban_lot_detail/md_lot_expiry_utils.js',
            'md_pharma_regulatory/static/src/kanban_lot_detail/kanban_lot_detail_popup.js',
            'md_pharma_regulatory/static/src/kanban_lot_detail/kanban_lot_detail_popup.xml',
            'md_pharma_regulatory/static/src/kanban_lot_detail/md_lot_detail_button.js',
            'md_pharma_regulatory/static/src/kanban_lot_detail/md_lot_detail_button.xml',
        ],
        # Solo se inyecta cuando el dark mode del backend está activo (mismo
        # patrón que medicine_depot_portal/backend_dark.scss) -- aplica el
        # tono oscuro real del POS (pos_glass_bento.scss) a esta card.
        'web.assets_web_dark': [
            'md_pharma_regulatory/static/src/scss/product_kanban_dark.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
