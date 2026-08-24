{
    "name": "CEP Verification — Banxico CEP-SCL",
    "version": "19.0.2.0.0",
    "category": "Accounting",
    "summary": "Verifica CEPs SPEI vía Banxico CEP-SCL (gratuito, sin APIs de pago)",
    "author": "Zorakode",
    "depends": ["base", "account", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/account_move_views.xml",
        "views/cep_verification_log_views.xml",
        "views/cep_scl_batch_views.xml",
        "views/cep_scl_batch_wizard_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
