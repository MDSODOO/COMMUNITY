# -*- coding: utf-8 -*-
{
    'name': 'Selección de Lotes — Ventas y Compras',
    'version': '19.0.1.1.1',
    'category': 'Tools',
    'author': 'Medicine Depot - Daniel Cervera',
    'license': 'OPL-1',
    'summary': 'Selección y asignación de lotes/series en órdenes de venta y compra con FEFO automático',
    'description': """
Unifica la gestión de lotes/series en órdenes de venta y compra:

Ventas:
  - Columna Lote/Serie en líneas de venta con FEFO automático.
  - Columna Caducidad (solo lectura) en líneas de venta.
  - Auto-selección del lote con caducidad más próxima al elegir producto.
  - Pre-asigna el lote al albarán de entrega al confirmar la orden.

Compras:
  - Columna Lote en líneas de compra (permite crear y editar lotes).
  - Columna Caducidad editable; sincronización automática OC → stock.lot.
  - Validación bloqueante: detiene confirmación si hay lotes sin fecha o vencidos.
  - Pre-asigna el lote al albarán de recepción al confirmar la OC.

Inventario:
  - Buscador de lotes/series reorganizado: "Número de lote/serie" como campo principal.
    """,
    'depends': [
        'sale',
        'sale_stock',
        'purchase',
        'purchase_stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/purchase_order_view.xml',
        'views/stock_lot_search_views.xml',
    ],
    'post_init_hook': '_post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
