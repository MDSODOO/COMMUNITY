from odoo import _, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_product_catalog_domain(self):
        """Filtra el catálogo a productos NO almacenables o con stock > 0 en el warehouse."""
        domain = super()._get_product_catalog_domain()

        warehouse = self.warehouse_id or self.env["stock.warehouse"].search(
            [("company_id", "=", self.company_id.id)], limit=1,
        )
        if not warehouse:
            return domain

        locations = self.env["stock.location"].search([
            ("warehouse_id", "=", warehouse.id),
            ("usage", "=", "internal"),
        ])
        product_ids_with_stock = []
        if locations:
            quant_groups = self.env["stock.quant"]._read_group(
                domain=[
                    ("location_id", "in", locations.ids),
                    ("company_id", "=", warehouse.company_id.id),
                    ("quantity", ">", 0),
                ],
                groupby=["product_id"],
                aggregates=["quantity:sum"],
            )
            product_ids_with_stock = [g[0].id for g in quant_groups if g[0]]

        stock_filter = [
            "|",
            ("is_storable", "=", False),
            ("id", "in", product_ids_with_stock),
        ]
        return domain + stock_filter

    def _notify_stock_clamped(self, product, requested, available, warehouse):
        """Dispara notificación al usuario informando el ajuste de cantidad.

        Usa dos canales de bus.bus para máxima cobertura:
          - 'simple_notification': toast estándar (manejado por bus_service nativo).
          - 'sale_stock_availability/clamp_dialog': abre AlertDialog vía servicio JS
            registrado por este módulo.
        """
        if not self.env.user or not self.env.user.partner_id:
            return
        title = _("Cantidad ajustada a la existencia a la mano")
        message = _(
            "Solicitaste %(req)s de «%(prod)s» pero solo hay %(av)s a la mano "
            "en %(wh)s. La cantidad fue ajustada automáticamente a %(av)s.",
            req=requested,
            prod=product.display_name,
            av=available,
            wh=warehouse.display_name,
        )
        bus = self.env["bus.bus"]
        bus._sendone(
            self.env.user.partner_id,
            "simple_notification",
            {
                "type": "warning",
                "title": title,
                "message": message,
                "sticky": True,
            },
        )
        bus._sendone(
            self.env.user.partner_id,
            "sale_stock_availability/clamp_dialog",
            {
                "title": title,
                "message": message,
            },
        )

    def action_confirm(self):
        """Red de seguridad final: re-clampa cantidades al On Hand actual antes
        de confirmar. Cubre el race condition entre creación de línea y confirmación.
        """
        for order in self:
            warehouse = order.warehouse_id
            if not warehouse:
                continue
            for line in order.order_line:
                if line.display_type or not line.product_id or not line.product_id.is_storable:
                    continue
                max_qty = line._max_qty_in_line_uom()
                if max_qty is None:
                    continue
                if line.product_uom_qty > max_qty:
                    requested = line.product_uom_qty
                    line.product_uom_qty = max_qty
                    order._notify_stock_clamped(
                        line.product_id, requested, max_qty, warehouse,
                    )
        return super().action_confirm()

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        """Clampa silenciosamente la cantidad al stock del warehouse y notifica."""
        product = self.env["product.product"].browse(product_id)
        warehouse = self.warehouse_id
        if product.is_storable and warehouse and quantity and quantity > 0:
            available = product._get_warehouse_available_qty(warehouse)
            if quantity > available:
                self._notify_stock_clamped(product, quantity, available, warehouse)
                quantity = available
        return super()._update_order_line_info(product_id, quantity, **kwargs)

    def _get_catalog_max_available(self, product_id):
        """Máximo A la mano para un producto en el warehouse de la orden."""
        self.ensure_one()
        product = self.env["product.product"].browse(product_id)
        if not product.exists() or not product.is_storable:
            return False
        warehouse = self.warehouse_id
        if not warehouse:
            return False
        return product._get_warehouse_available_qty(warehouse)
