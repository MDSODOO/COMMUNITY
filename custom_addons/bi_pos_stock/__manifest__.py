# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Stock in Odoo — Multi-Branch Edition',
    'version': '19.0.7.1',  # migración columna "Línea" de x_line (Studio, 0% poblado) a md.product.line (97% poblado)
    "category": "Point of Sale",
    "depends": ['base', 'sale_management', 'stock', 'point_of_sale', 'mail', 'md_product_lines'],
    "external_dependencies": {
        "python": ["openpyxl"],
    },
    'author': 'Medicine Depot - Daniel Cervera',
    'summary': (
        'Branch-scoped POS stock display. Shows only the stock of the warehouse '
        'linked to the active POS session. Cross-branch data never reaches the browser.'
    ),
    "description": """
    Multi-branch POS stock module.

    Security model:
      - Stock quantities are pre-computed per branch on the server side.
      - Only this branch's warehouse stock is sent to the POS frontend.
      - No quant_text (cross-branch data blob) is ever serialized to the client.
      - Frontend only displays pre-filtered data — no client-side location filtering.

    Features:
      - Branch-scoped stock badges on product cards (top-left/top-right/bottom-right).
      - Cantidad en mano (A la mano) o cantidad en tránsito por sucursal.
      - Bloqueo de órdenes cuando el stock A la mano de la sucursal sea cero (umbral configurable).
      - Low Stock Product List filtered by branch.
      - Real-time stock updates via websocket (post-commit, deadlock-safe).
      - Self-Order (kiosk) integration with same branch restrictions.
      - Reporte Z farmaceutico por correo con Excel adjunto, cliente, POS Order, timestamp, lote y caducidad.
      - Resumen del Excel con ordenes POS y cliente asociado.
      - Clasificacion de factura individual, global, global pendiente o sin factura en el Excel.
      - Concentrado diario de sesiones/cajas por punto de venta en el Excel.
      - Envio del Reporte Z usando remitente compatible con el FROM Filtering de Odoo.
      - Acciones manuales temporales de validacion removidas del menu de pos.session.
      - Reporte PDF Detalles de ventas con trazabilidad farmaceutica y sin barcode.
    """,
    "website": "https://www.browseinfo.com",
    "data": [
        'security/ir.model.access.csv',
        'views/bi_supplier_snapshot_views.xml',
        'views/custom_pos_config_view.xml',
        'views/pos_order_views.xml',
        'views/pos_viewport_fix.xml',
        'views/pos_z_report_templates.xml',
        'views/pos_session_sales_details_report.xml',
        'views/corte_z_report_templates.xml',
        'data/pos_z_report_actions.xml',
        'data/corte_z_report_data.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'bi_pos_stock/static/src/css/stock.css',
            # POS dynamic product URLs must bypass stale/offline service-worker caches.
            'bi_pos_stock/static/src/app/service_worker_bypass.js',
            # Silencia errores de consola: /pos/ping network failures + unhandled rejections.
            # Cargado antes que cualquier otro módulo para que el interceptor de fetch
            # esté activo desde el primer request de conectividad del POS.
            'bi_pos_stock/static/src/app/network/pos_ping_silence.js',
            # Store/models patches (PosStore.processServerData, addLineToOrder, PosOrder helper)
            # Also patches ECOMMERCE_ORDER bus subscription + EcommerceOrderPopup import
            'bi_pos_stock/static/src/app/store/models.js',
            # Order persistence patch: flushes open orders to IDB on visibilitychange/pagehide
            # Prevents order loss when screensaver activates or the OS locks the screen.
            'bi_pos_stock/static/src/app/store/order_persistence_patch.js',
            # Orderline lot patch: prevents merging lines that carry different lot assignments.
            # Ensures each lot selection in the cart stays as its own independent line.
            'bi_pos_stock/static/src/app/store/orderline_lot_patch.js',
            # Shared FEFO lot/stock helpers (getFefoLots, getLotStock, assignLotToLine) —
            # loaded before lot_cascade_patch.js and product_list.js, both of which import it.
            'bi_pos_stock/static/src/app/utils/lot_stock_utils.js',
            # Lot cascade patch: when qty exceeds a lot's stock, caps the line and
            # auto-creates new lines for the overflow using subsequent FEFO lots.
            'bi_pos_stock/static/src/app/store/lot_cascade_patch.js',
            # Orderline discount patch: PosOrderline.getEffectiveDiscountInfo() — deriva el
            # % de descuento cuando viene de un pricelist (Odoo nunca llena line.discount
            # en ese caso, solo el numpad lo hace). Usado por OrderlineInlineDiscount abajo.
            'bi_pos_stock/static/src/app/store/orderline_discount_patch.js',
            # Shared expiry helpers (getDaysLeft, getExpiryColorClass, formatExpiryDate,
            # formatQty) — cargado antes de lot_label_patch.js, que ya los usa.
            'bi_pos_stock/static/src/app/utils/lot_expiry_utils.js',
            # Lot label patch: "<cantidad> Lote <código> <fecha de caducidad>" en vez del
            # "Lot Number <código>" (sin cantidad ni fecha) hardcodeado en inglés por el
            # core de Odoo (no está envuelto en _t(), no hay .po que lo traduzca).
            'bi_pos_stock/static/src/app/store/lot_label_patch.js',
            # ProductCard prop declaration and XML template (badge display)
            'bi_pos_stock/static/src/app/generic_components/product_card/product_card.js',
            'bi_pos_stock/static/src/app/generic_components/product_card/product_card.xml',
            # LotSelectionPopup: FEFO stepper table opened when the cashier taps a
            # lot/serial-tracked ProductCard — loaded before product_list.js, which opens it.
            'bi_pos_stock/static/src/app/components/lot_selection_popup/lot_selection_popup.js',
            'bi_pos_stock/static/src/app/components/lot_selection_popup/lot_selection_popup.xml',
            # ProductScreen patches: _recomputeTemplateStock, addProductToOrder, pay()
            'bi_pos_stock/static/src/app/screens/product_screen/product_list/product_list.js',
            # OrderSummary patch: numpad and +/- button stock limit enforcement
            'bi_pos_stock/static/src/app/screens/product_screen/order_summary/order_summary.js',
            # Unified Stock screen (per-month sales + orderpoint restock + Matrix warehouse transfers)
            'bi_pos_stock/static/src/app/screens/replenishment_screen/replenishment_line/replenishment_line.js',
            'bi_pos_stock/static/src/app/screens/replenishment_screen/replenishment_line/replenishment_line.xml',
            'bi_pos_stock/static/src/app/screens/replenishment_screen/replenishment_screen.js',
            'bi_pos_stock/static/src/app/screens/replenishment_screen/replenishment_screen.xml',
            # E-commerce orders screen
            'bi_pos_stock/static/src/app/screens/ecommerce_orders_screen/ecommerce_orders_screen.js',
            'bi_pos_stock/static/src/app/screens/ecommerce_orders_screen/ecommerce_orders_screen.xml',
            # E-commerce new-order popup (shown on ECOMMERCE_ORDER bus message)
            'bi_pos_stock/static/src/app/components/ecommerce_order_popup/ecommerce_order_popup.js',
            'bi_pos_stock/static/src/app/components/ecommerce_order_popup/ecommerce_order_popup.xml',
            # ClosePosPopup: replace "Daily Sale" with the standardized cash-close PDF.
            'bi_pos_stock/static/src/app/components/closing_popup/closing_popup.js',
            'bi_pos_stock/static/src/app/components/closing_popup/closing_popup.xml',
            # ── Lot / FEFO features ───────────────────────────────────────────
            # (lot_expiry_utils.js ya se cargó arriba, antes de lot_label_patch.js)
            # LotDetailPopup: full FEFO breakdown opened from ProductCard ⓘ button
            'bi_pos_stock/static/src/app/components/lot_detail_popup/lot_detail_popup.js',
            'bi_pos_stock/static/src/app/components/lot_detail_popup/lot_detail_popup.xml',
            # SelectLotPopup patch: FEFO guide table + expiry badges in lot selector
            'bi_pos_stock/static/src/app/components/select_lot_popup_patch/select_lot_popup_patch.js',
            'bi_pos_stock/static/src/app/components/select_lot_popup_patch/select_lot_popup_patch.xml',
            # Order widget (Total Items counter — unrelated to stock, kept as-is)
            'bi_pos_stock/static/src/app/generic_components/order_widget/order_widget.js',
            'bi_pos_stock/static/src/app/generic_components/order_widget/order_widget.xml',
            # Navbar (Stock + Pedidos en Línea buttons)
            'bi_pos_stock/static/src/app/navbar/navbar.js',
            'bi_pos_stock/static/src/app/navbar/navbar.xml',
            # OrderReceipt: encabezado de columnas "Producto | Precio" en el ticket 80mm
            'bi_pos_stock/static/src/app/generic_components/order_receipt/order_receipt.xml',
            # ── Layout overrides — load LAST so cascade order also favours our rules ──
            # Higher-specificity selectors (.pos .leftpane, .pos .product-list, etc.)
            # guarantee the override regardless of order, but trailing position is best
            # practice. Uses Bootstrap 5 mixins (available in Odoo 19 SCSS bundle context).
            'bi_pos_stock/static/src/scss/pos_custom_layout.scss',
            # ProductCard flex-column layout + lot-card-footer transition
            # Loaded after pos_custom_layout.scss so min-height overrides win on cascade
            'bi_pos_stock/static/src/scss/pos_product_card.scss',
            # Reformato del ticket de cliente (OrderReceipt) para impresión térmica 80mm —
            # loaded after pos_custom_layout.scss/stock.css so its .md-order-stats overrides win.
            'bi_pos_stock/static/src/scss/pos_receipt_print.scss',
            # Glassmorphism + Bento redesign (ProductScreen + FEFO lot popups) — loaded LAST
            # so it wins cascade ties against every rule above (see file header for the
            # "dark fixed" strategy and the pos-force-light escape hatch).
            'bi_pos_stock/static/src/scss/pos_glass_bento.scss',
        ],
        'web.assets_backend': [
            # Responsive styles for POS reports rendered in the browser backend.
            'bi_pos_stock/static/src/scss/pos_reports_web.scss',
        ],
        'pos_self_order.assets': [
            'bi_pos_stock/static/src/app/self_order/css/stock.css',
            'bi_pos_stock/static/src/app/self_order/self_order.xml',
            'bi_pos_stock/static/src/app/self_order/self_order_product.js',
            'bi_pos_stock/static/src/app/self_order/bi_warning_popup.js',
            'bi_pos_stock/static/src/app/self_order/bi_warning_popup.xml',
        ],
    },
    'post_init_hook': 'post_init_hook',
    "auto_install": False,
    "installable": True,
    "images": ['static/description/Banner.gif'],
    'license': 'OPL-1',
}
