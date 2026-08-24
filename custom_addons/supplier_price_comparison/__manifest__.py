{
    "name": "Consolidador de Precios (Excel)",
    "summary": "Consolida precios de Levic, Farmater y Brudifarma en un archivo base Excel",
    "author": "Daniel Cervera / QUIFAMESA",
    "website": "https://www.quifamesa.com",
    "category": "Inventory/Purchase",
    "version": "19.0.1.0.2",
    "license": "LGPL-3",
    "depends": ["base", "purchase"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/price_comparison_views.xml",
        "wizard/import_base_catalog_views.xml",
        "wizard/import_supplier_catalog_views.xml",
        "wizard/consolidate_supplier_prices_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "supplier_price_comparison/static/src/scss/price_comparison.scss",
        ],
        # Odoo 19 carga este bundle SOLO cuando el dark mode está activo.
        # No se necesitan selectores .o_dark_mode ni [data-bs-theme].
        "web.assets_web_dark": [
            "supplier_price_comparison/static/src/scss/backend_dark.scss",
        ],
    },
    "external_dependencies": {
        "python": ["openpyxl", "xlrd"],
    },
    "installable": True,
    "application": True,
}
