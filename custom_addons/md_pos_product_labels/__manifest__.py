{
    'name': 'MDS - Etiquetas de Producto en POS',
    'summary': 'Replica en la card de producto del Punto de Venta las etiquetas de Linea/Forma/Concentracion/Contenido/Envase/Talla/Sustancia Activa ya usadas en el kanban de Inventario, mas un popup de detalle regulatorio completo y busqueda reforzada.',
    'version': '19.0.2.0.0',
    'category': 'Point of Sale',
    'author': 'MedicineDepot Sureste',
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'md_pharma_regulatory', 'md_product_lines'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'md_pos_product_labels/static/src/js/color_utils.js',
            'md_pos_product_labels/static/src/js/product_card.js',
            'md_pos_product_labels/static/src/js/product_template_search_patch.js',
            'md_pos_product_labels/static/src/components/regulatory_detail_popup/regulatory_detail_popup.js',
            'md_pos_product_labels/static/src/components/regulatory_detail_popup/regulatory_detail_popup.xml',
            'md_pos_product_labels/static/src/xml/product_card.xml',
            'md_pos_product_labels/static/src/scss/product_card.scss',
        ],
    },
    'installable': True,
    'application': False,
}
