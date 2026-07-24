from odoo import fields, models


class LegacyPosOrder(models.Model):
    _name = "md.legacy.pos.order"
    _description = "Pedido de PoS histórico (Microsip, solo lectura)"
    _order = "date desc"
    _rec_name = "folio"

    legacy_ref = fields.Char(required=True, index=True)
    folio = fields.Char(string="Folio")
    date = fields.Date(string="Fecha")
    company_id = fields.Many2one("res.company", string="Sucursal")
    partner_id = fields.Many2one("res.partner", string="Cliente")
    state = fields.Selection(
        [("normal", "Normal"), ("cancelado", "Cancelado"), ("otro", "Otro")],
        string="Estado",
    )
    amount_total = fields.Monetary(string="Total")
    currency_id = fields.Many2one("res.currency", string="Moneda")
    line_ids = fields.One2many("md.legacy.pos.order.line", "order_id", string="Líneas")

    _legacy_ref_uniq = models.Constraint(
        "UNIQUE(legacy_ref)", "Ya existe un pedido con esa referencia legacy."
    )


class LegacyPosOrderLine(models.Model):
    _name = "md.legacy.pos.order.line"
    _description = "Línea de pedido de PoS histórico (Microsip, solo lectura)"

    order_id = fields.Many2one("md.legacy.pos.order", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Producto")
    quantity = fields.Float(string="Cantidad")
    price_unit = fields.Float(string="Precio unitario")
    price_subtotal = fields.Monetary(string="Subtotal")
    currency_id = fields.Many2one(related="order_id.currency_id")
