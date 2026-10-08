# -*- coding: utf-8 -*-
{
    'name': 'Reportes Farmacéuticos',
    'version': '19.0.1.0.21',
    'category': 'Reporting',
    'author': 'Medicine Depot, Daniel Cervera',
    'website': 'https://www.medicinedepotsureste.mx',
    'license': 'OPL-1',
    'summary': 'Reportes PDF farmacéuticos para ventas, entregas y órdenes de compra con lote y caducidad',
    'description': """
Unifica los reportes farmacéuticos de Medicine Depot:

  - Orden de Venta / Cotización: columnas Lote, Caducidad, Desc.%
  - Albarán de Entrega: diseño pharma consistente.
  - Orden de Compra / RFQ: columnas Lote y Caducidad.

Incluye:
  - Header pharma con logo, franja de color, meta-banda y bloque de dirección.
  - Paperformat personalizado para OC y RFQ (márgenes optimizados para wkhtmltopdf).
  - SCSS farmacéutico (paleta brand/teal/lime) compartida entre todos los reportes.
    """,
    'depends': [
        'base',
        'web',
        'stock',
        'sale_stock',
        'purchase',
        'product_expiry',
        'lot_selection',
        'custom_invoice_format',
    ],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'data': [
        'report/report_layout_overrides.xml',
        'report/account_invoice_cfdi_report.xml',
        'report/sale_order_header.xml',
        'report/sale_order_paperformat.xml',
        'report/sale_order_report.xml',
        'report/stock_delivery_report.xml',
        'report/stock_transfer_report.xml',
        'report/purchase_order_paperformat.xml',
        'report/purchase_order_report.xml',
        # Inventario Físico — mejora UI tree view + reporte PDF
        'report/physical_inventory_view.xml',
        'report/physical_inventory_report.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'pharma_reports/static/src/scss/pharma_report.scss',
            'pharma_reports/static/src/scss/sale_report.scss',
            'pharma_reports/static/src/scss/purchase_report.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
