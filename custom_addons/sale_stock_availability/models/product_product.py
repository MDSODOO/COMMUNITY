from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_warehouse_available_qty(self, warehouse):
        """On Hand (qty_available) del producto en el warehouse dado.

        Regla de negocio: NO descuenta reservas. Devuelve la cantidad físicamente
        en ubicaciones internas del warehouse, scoped a la compañía del warehouse.
        """
        self.ensure_one()
        if not warehouse:
            return 0.0
        if not self.is_storable:
            return float("inf")
        product = self.with_company(warehouse.company_id).with_context(
            warehouse_id=warehouse.id,
            location=False,
        )
        return product.qty_available
