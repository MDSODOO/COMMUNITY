{
    'name': "Cart Barcode Scanner (A la mano)",
    'author': "Medicine Depot - Daniel Cervera",
    'summary': "Escaneo de codigo de barras por camara en el carrito de eCommerce, con validacion 'A la mano'",
    'version': "19.0.1.0.0",
    'category': "Website/Website",
    'license': "LGPL-3",
    'depends': ["website_sale", "custom_shop_qty_selector", "medicine_depot_portal"],
    'data': [
        "views/templates.xml",
    ],
    'assets': {
        "web.assets_frontend": [
            # Libreria vendorizada localmente (no CDN) para respetar CSP y
            # evitar dependencia de un tercero en produccion.
            "md_cart_barcode_scanner/static/lib/html5-qrcode/html5-qrcode.min.js",
            "md_cart_barcode_scanner/static/src/scss/cart_barcode_scanner.scss",
            "md_cart_barcode_scanner/static/src/xml/cart_barcode_scanner.xml",
            "md_cart_barcode_scanner/static/src/js/cart_barcode_scanner.js",
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
