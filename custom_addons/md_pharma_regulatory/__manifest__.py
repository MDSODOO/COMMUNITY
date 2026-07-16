{
    'name': 'Medicine Depot - Homologación Regulatoria COFEPRIS',
    'version': '19.0.9.0.0',
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
    'depends': ['product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/active_substance_views.xml',
        'views/abbreviation_views.xml',
        'views/product_template_views.xml',
        'views/product_visual_views.xml',
        'views/regulatory_review_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
