from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    x_transfer_approver_id = fields.Many2one(
        "res.users",
        string="Aprobador de traslados internos",
        help="Usuario que recibe la actividad de aprobación cuando esta "
        "sucursal es el destino de una transferencia interna. Si está "
        "vacío, la actividad se asigna al grupo Encargados de Almacén "
        "completo (ver security/md_stock_transfer_approval_security.xml).",
    )
