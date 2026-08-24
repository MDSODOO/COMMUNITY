# -*- coding: utf-8 -*-
{
    "name": "Factura Global CFDI 4.0",
    "version": "19.0.1.1.0",
    "category": "Tools",
    "author": "INFLEXYON",
    "license": "OPL-1",
    "summary": "Generacion de facturas globales apartir de las ordenes del POS",
    "description": """Generacion de facturas globales apartir de las ordenes del POS.

Adaptado para Odoo Community: reemplaza la dependencia de l10n_mx_edi
(Enterprise) por l10n_mx_cfdi_account (OCA, repo l10n-mexico). Este modulo
sigue encargandose de agrupar ordenes POS/ventas sin factura en una sola
factura (is_global_invoice=True); el timbrado real como CFDI 'Publico en
general' lo hace el wizard ya existente de l10n_mx_cfdi_account
(generic_invoice_create), no se reimplemento aqui.""",
    "depends": [
        "account",
        "l10n_mx_cfdi_account",
        "point_of_sale",
        "sale",
    ],
    "data": [
        "data/data_global_invoice.xml",
        "data/cron_global_invoice.xml",
        "security/invoice_global_security.xml",
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/pos_order_views.xml",
        "views/res_config_settings.xml",
        "wizard/pos_order_make_invoice_view.xml",
        "wizard/sale_order_make_invoice.xml",
        "data/hide_native_global_invoice_action.xml",
    ],
    "assets": {
        # web assets
        "point_of_sale._assets_pos": [
            "l10n_mx_edi_global_invoice/static/src/js/close_pos_popup.js",
        ]
    },
    "application": True,
    "installable": True,
    "auto_install": False,
    "website": "https://www.inflexyon.mx",
}
