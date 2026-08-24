{
    "name": "Importador de Costos de Proveedores",
    "summary": "Importa y actualiza costos de productos desde archivos Excel de proveedores",
    "author": "Daniel Cervera / QUIFAMESA",
    "website": "https://www.quifamesa.com",
    "category": "Inventory/Purchase",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": [
        "base",
        "purchase",
        "stock",
        "supplier_price_comparison",
    ],
    "external_dependencies": {
        "python": ["openpyxl", "xlrd"],
    },
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "wizard/import_quifa_cost_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
}
