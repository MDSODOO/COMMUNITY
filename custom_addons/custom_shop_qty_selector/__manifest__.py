{
    'name': "Shop Quantity Selector & A la mano",
    'author': "Medicine Depot - Daniel Cervera",
    'summary': "Qty pill + A la mano badge on shop grid; A la mano box + vertical CTA on product detail",
    'version': "19.0.2.21.0",
    'category': "Website/Website",
    'license': "LGPL-3",
    'depends': [
        "website_sale",
        "website_sale_stock",
        "website_sale_wishlist",
        "website_sale_collect",
        "point_of_sale",
    ],
    'data': [
        'security/ir.model.access.csv',
        "views/templates.xml",
        "views/website_sale_cart_i18n.xml",
    ],
    'post_init_hook': '_post_init_create_studio_acls',
    'uninstall_hook': '_uninstall_cleanup_studio_acls',
    'assets': {
        "web.assets_frontend": [
            "custom_shop_qty_selector/static/src/scss/shop_qty_selector.scss",
            "custom_shop_qty_selector/static/src/js/shop_qty_selector.js",
            "custom_shop_qty_selector/static/src/js/shop_filters_patch.js",
            "custom_shop_qty_selector/static/src/xml/product_availability.xml",
            "custom_shop_qty_selector/static/src/xml/click_and_collect_availability.xml",
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
