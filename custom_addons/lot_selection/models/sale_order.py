from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        res = super().action_confirm()

        for order in self:
            for line in order.order_line.filtered(lambda l: l.lot_id):
                moves = line.move_ids.filtered(
                    lambda m: m.state not in ("cancel", "done")
                )
                for move in moves:
                    if move.move_line_ids:
                        move.move_line_ids.write({"lot_id": line.lot_id.id})
                    else:
                        # En Odoo 17+ el campo puede llamarse 'quantity' en lugar
                        # de 'reserved_uom_qty'. Se detecta en tiempo de ejecución
                        # para ser compatible con distintas versiones de Odoo 19.
                        sml_fields = self.env["stock.move.line"]._fields
                        qty_field = (
                            "reserved_uom_qty"
                            if "reserved_uom_qty" in sml_fields
                            else "quantity"
                        )
                        self.env["stock.move.line"].create({
                            "move_id": move.id,
                            "product_id": move.product_id.id,
                            "product_uom_id": move.product_uom.id,
                            "location_id": move.location_id.id,
                            "location_dest_id": move.location_dest_id.id,
                            "lot_id": line.lot_id.id,
                            qty_field: move.product_uom_qty,
                        })

        return res
