from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    lot_domain = fields.Binary(
        compute="_compute_lot_domain",
        store=False,
    )

    lot_id = fields.Many2one(
        "stock.lot",
        string="Lote/Serie",
        domain="lot_domain",
        readonly=False,
    )

    # Solo lectura en ventas: el usuario puede ver la fecha pero no modificarla.
    lot_expiration_date = fields.Datetime(
        related="lot_id.expiration_date",
        string="Fecha de Caducidad",
        store=False,
        readonly=True,
    )

    @api.depends("product_id", "order_id.warehouse_id")
    def _compute_lot_domain(self):
        """
        Solo escribe en lot_domain, nunca en lot_id.
        Filtra por existencia a la mano en el almacén (FEFO: más próximo a caducar primero).
        """
        for line in self:
            if not line.product_id or line.product_id.tracking not in ("lot", "serial"):
                line.lot_domain = [("id", "=", 0)]
                continue

            warehouse = line.order_id.warehouse_id
            if not warehouse:
                line.lot_domain = [("id", "=", 0)]
                continue

            locations = self.env["stock.location"].search([
                ("id", "child_of", warehouse.lot_stock_id.id),
                ("usage", "=", "internal"),
            ])

            quants = self.env["stock.quant"].search([
                ("product_id", "=", line.product_id.id),
                ("location_id", "in", locations.ids),
                ("quantity", ">", 0),
                ("lot_id", "!=", False),
            ])

            lots = quants.mapped("lot_id").sorted(
                key=lambda l: l.expiration_date or l.use_date or fields.Datetime.max
            )

            line.lot_domain = [("id", "in", lots.ids)] if lots else [("id", "=", 0)]

    @api.onchange("product_id", "order_id")
    def _onchange_product_set_lot(self):
        """Auto-selecciona el lote con caducidad más próxima (FEFO)."""
        for line in self:
            if not line.product_id or line.product_id.tracking not in ("lot", "serial"):
                line.lot_id = False
                continue

            warehouse = line.order_id.warehouse_id
            if not warehouse:
                line.lot_id = False
                continue

            locations = self.env["stock.location"].search([
                ("id", "child_of", warehouse.lot_stock_id.id),
                ("usage", "=", "internal"),
            ])

            quants = self.env["stock.quant"].search([
                ("product_id", "=", line.product_id.id),
                ("location_id", "in", locations.ids),
                ("quantity", ">", 0),
                ("lot_id", "!=", False),
            ])

            lots = quants.mapped("lot_id").sorted(
                key=lambda l: l.expiration_date or l.use_date or fields.Datetime.max
            )

            if lots:
                if not line.lot_id or line.lot_id not in lots:
                    line.lot_id = lots[0]
            else:
                line.lot_id = False

    picking_lot_ids = fields.Many2many(
        "stock.lot",
        string="Lotes Enviados",
        compute="_compute_picking_lots",
        store=False,
    )

    @api.depends("move_ids.move_line_ids.lot_id")
    def _compute_picking_lots(self):
        for line in self:
            line.picking_lot_ids = line.move_ids.mapped("move_line_ids.lot_id")
