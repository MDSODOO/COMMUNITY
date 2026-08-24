# -*- coding: utf-8 -*-
{
    "name": "Descarga Masiva de XML del SAT",
    "version": "19.0.1.1.3",
    "category": "Accounting/Localizations",
    "summary": "Descarga masiva de CFDI (XML) desde el Web Service del SAT "
    "usando la e.firma (FIEL)",
    "description": """
Módulo para la descarga masiva de archivos XML (CFDI) directamente desde el
Web Service del SAT (Servicio de Administración Tributaria de México).

Funcionalidades principales:
- Gestión segura de la FIEL (.cer, .key y contraseña)
- Consumo del Web Service del SAT (Autenticación, Solicitud, Verificación, Descarga)
- Procesamiento asíncrono mediante cron jobs (compatible con Odoo.sh)
- Almacenamiento intermedio de XMLs descargados antes de crear/conciliar facturas
    """,
    "author": "QUIFAMESA Custom Development",
    "website": "https://www.quifamesa.com",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "external_dependencies": {
        "python": [
            "cryptography",
            "lxml",
            "requests",
            "OpenSSL",
        ],
    },
    "data": [
        "security/sat_download_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/res_company_views.xml",
        "views/sat_download_request_views.xml",
        "views/sat_xml_document_views.xml",
        "views/sat_download_menuitem.xml",
        "wizards/sat_download_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
