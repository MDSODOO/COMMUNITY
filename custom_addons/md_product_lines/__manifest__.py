{
    'name': 'MDS - Líneas de Producto',
    'summary': 'Modelo dedicado "Línea" separado de la categoría de producto estándar, para poder usar categ_id con otro fin. / Dedicated "Line" model separate from the standard product category, freeing categ_id for another purpose.',
    'version': '19.0.2.0.0',
    'category': 'Inventory',
    'author': 'MedicineDepot Sureste',
    'license': 'LGPL-3',
    'depends': ['product'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_line_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
}
