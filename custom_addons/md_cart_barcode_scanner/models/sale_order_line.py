from odoo import models

from odoo.addons.custom_shop_qty_selector.controllers.main import (
    resolve_warehouse,
    lot_filtered_stock_qty_map,
)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _md_qty_a_la_mano(self):
        """Cantidad 'A la mano' (On Hand) para el producto de esta linea,
        con el mismo criterio de resolve_warehouse()/lot_filtered_stock_qty_map
        que ya usa el resto del sitio (custom_shop_qty_selector). Devuelve
        None para productos no storables (sin limite fisico que mostrar en
        el badge del carrito).
        """
        self.ensure_one()
        product = self.product_id
        if not product or not product.is_storable:
            return None
        warehouse_id = resolve_warehouse()
        if warehouse_id is None:
            return None
        if product.tracking in ('lot', 'serial'):
            return lot_filtered_stock_qty_map(product, warehouse_id).get(product.id, 0)
        return max(0, int(product.with_context(warehouse_id=warehouse_id).free_qty or 0))
