{
    "name": "Portal Picking Visibility",
    "summary": (
        "Expone órdenes con albaranes activos en el portal del cliente "
        "y muestra el estado de envío en /my/orders."
    ),
    "version": "19.0.1.1.0",
    "category": "Inventory/Logistics",
    "author": "Medicine Depot",
    "license": "LGPL-3",
    "depends": [
        "sale",
        "stock",
        "website_sale",
        "portal",
        "medicine_depot_portal",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/portal_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "portal_picking_visibility/static/src/scss/portal_picking.scss",
        ],
    },
    "post_init_hook": "_post_init_compute_delivery_status",
    "demo": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
