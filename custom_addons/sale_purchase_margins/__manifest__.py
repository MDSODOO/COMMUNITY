{
    'name': 'Márgenes de Compra y Venta',
    'version': '19.0.2.0.8',
    'category': 'Sales,Purchases',
    'summary': 'Cálculo y visualización de márgenes en líneas de venta y compra',
    'description': '''
        Módulo que agrega campos computados para márgenes de venta y compra.

        Características:
        - Márgenes de venta (porcentaje e importe) en sale.order.line
        - Márgenes de compra (porcentaje e importe) en purchase.order.line
        - Alertas automáticas para márgenes negativos
        - Campos readonly, computados con @api.depends
        - Recalculan automáticamente al cambiar precio o producto
    ''',
    'author': 'Daniel Cervera / QUIFAMESA',
    'website': 'https://quifamesa.mx',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'purchase',
        'account',
        'stock',
        'purchase_stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/stock_orderpoint_actions.xml',
        'views/sale_margin_line_rule_view.xml',
        'views/product_template_view.xml',
        'views/sale_order_view.xml',
        'views/purchase_order_view.xml',
        'views/res_config_settings_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
