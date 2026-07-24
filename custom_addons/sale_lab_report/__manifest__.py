{
    'name': 'sale_lab_report',
    'version': '19.0.1.0.0',
    'category': 'Sales/Reporting',
    'summary': 'Tabla dinámica de Ventas Laboratorio agrupada por Producto y Sucursal',
    'description': '''
        Añade el menú "Ventas Laboratorio" bajo Ventas > Reportes: una tabla
        dinámica (pivot) de sale.report preconfigurada para las líneas de
        laboratorio SERRAL, RAAM, PERRIGO - QUIFA, LIFERPAL,
        GELCAPS/PHARMACAPS y CMD, agrupada por Producto y Sucursal
        (Almacén), con columnas por mes.
    ''',
    'author': 'Daniel-Cervera',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'sale_stock',
        'md_product_lines',
    ],
    'data': [
        'views/sale_report_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
