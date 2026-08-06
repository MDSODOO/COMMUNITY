# -*- coding: utf-8 -*-
{
    "name": "MDS - Navbar Style & OWL Extension",
    "summary": "Rediseño corporativo MDS de la barra superior y extensión OWL para Odoo 19.",
    "version": "19.0.1.1.0",
    "category": "Themes",
    "author": "MedicineDepot Sureste",
    "license": "LGPL-3",
    "depends": ["web"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "md_navbar_style/static/src/scss/navbar_style.scss",
            "md_navbar_style/static/src/js/navbar_patch.js",
            "md_navbar_style/static/src/xml/navbar_templates.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
