{
    "name": "MDS Stock Transfer Approval",
    "version": "19.0.1.0.0",
    "category": "Inventory",
    "summary": "Aprobación con doble candado de evidencia fotográfica para transferencias internas entre sucursales",
    "description": """
Extiende stock.picking (transferencias internas, picking_type_id.code == 'internal')
con un flujo de aprobación paralelo al ciclo de vida nativo de Odoo, sin reemplazar
el campo 'state' estándar de inventario.

Requiere dos evidencias fotográficas obligatorias antes de poder solicitar
aprobación (candado de producto + candado de empaque), asigna la aprobación al
responsable de la sucursal destino, y bloquea la validación del traslado
(button_validate) mientras no esté aprobado.

Diseño documentado en docs/arquitectura_traspasos_aprobacion_evidencias.md
(repo compartido pmo-trazabilidad). No adapta el patrón de
medicine_depot_scrap_batch porque ese módulo no tiene evidencia fotográfica
ni approval_user_id/date -- se audito su código real antes de diseñar esto.
""",
    "author": "Medicine Depot",
    "license": "LGPL-3",
    "depends": ["stock", "mail"],
    "data": [
        "security/md_stock_transfer_approval_security.xml",
        "security/ir.model.access.csv",
        "data/ir_config_parameter_data.xml",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "application": False,
}
