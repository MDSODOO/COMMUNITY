from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_warehouse_for_stock(self):
        self.ensure_one()
        return self.order_id.warehouse_id

    def _max_qty_in_line_uom(self):
        """Cantidad máxima vendible en la UoM de la línea, scoped al warehouse de la orden."""
        self.ensure_one()
        product = self.product_id
        uom = self.product_uom_id
        if not product or not uom or not product.is_storable:
            return None
        warehouse = self._get_warehouse_for_stock()
        if not warehouse:
            return None
        available = product._get_warehouse_available_qty(warehouse)
        return product.uom_id._compute_quantity(available, uom)

    def _exceeds_available_stock(self):
        self.ensure_one()
        if not self.product_id or not self.product_id.is_storable:
            return False
        if self.state in ("sale", "done", "cancel"):
            return False
        if self.display_type:
            return False
        max_qty = self._max_qty_in_line_uom()
        if max_qty is None:
            return False
        return self.product_uom_qty > max_qty

    def _clamp_vals_to_stock(self, vals, warehouse, order=None, fallback_product=None, fallback_uom=None):
        """Modifica vals in-place clampando product_uom_qty al stock del warehouse."""
        if vals.get("display_type"):
            return
        if "product_uom_qty" not in vals:
            return
        qty = vals.get("product_uom_qty")
        if qty is None:
            return

        product_id = vals.get("product_id") or (fallback_product.id if fallback_product else None)
        if not product_id:
            return
        product = self.env["product.product"].browse(product_id)
        if not product.is_storable:
            return
        if not warehouse:
            return

        uom_id = vals.get("product_uom_id")
        if uom_id:
            uom = self.env["uom.uom"].browse(uom_id)
        elif fallback_uom:
            uom = fallback_uom
        else:
            uom = product.uom_id

        available = product._get_warehouse_available_qty(warehouse)
        max_qty = product.uom_id._compute_quantity(available, uom)
        if qty > max_qty:
            vals["product_uom_qty"] = max_qty
            if order is not None:
                order._notify_stock_clamped(product, qty, max_qty, warehouse)

    def _write_vals_are_noop(self, vals):
        """Return True when vals would not change this line.

        Avoiding no-op writes matters because every sale.order.line write can
        recompute monetary fields on sale.order and increase serialization
        conflicts under concurrent website/POS activity.
        """
        self.ensure_one()
        for field_name, value in vals.items():
            if field_name == "product_uom_qty":
                rounding = self.product_uom_id.rounding if self.product_uom_id else 0.01
                if float_compare(
                    self.product_uom_qty,
                    value,
                    precision_rounding=rounding,
                ) != 0:
                    return False
                continue
            if field_name == "product_id":
                if self.product_id.id != value:
                    return False
                continue
            if field_name == "product_uom_id":
                if self.product_uom_id.id != value:
                    return False
                continue
            return False
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order_id = vals.get("order_id")
            if not order_id:
                continue
            order = self.env["sale.order"].browse(order_id)
            self._clamp_vals_to_stock(vals, order.warehouse_id, order=order)
        return super().create(vals_list)

    def write(self, vals):
        if "product_uom_qty" not in vals and "product_id" not in vals:
            return super().write(vals)

        # Líneas bloqueadas (sale/done/cancel): escribir en lote sin clamping.
        # El write individual anterior causaba N queries y fragmentaba el batch
        # de constraints, aumentando el riesgo de ValidationError por concurrencia.
        locked = self.filtered(lambda l: l.state in ("sale", "done", "cancel"))
        if locked:
            super(SaleOrderLine, locked).write(vals)

        # Líneas en borrador/enviadas: clampar qty por línea (cada producto
        # tiene distinta disponibilidad), luego escribir individualmente.
        for line in self - locked:
            line_vals = dict(vals)
            self._clamp_vals_to_stock(
                line_vals,
                line.order_id.warehouse_id,
                order=line.order_id,
                fallback_product=line.product_id,
                fallback_uom=line.product_uom_id,
            )
            if not line._write_vals_are_noop(line_vals):
                super(SaleOrderLine, line).write(line_vals)
        return True

    @api.constrains("product_uom_qty", "product_id", "product_uom_id")
    def _check_qty_available(self):
        for line in self:
            if line._exceeds_available_stock():
                max_qty = line._max_qty_in_line_uom() or 0
                raise ValidationError(_(
                    "No es posible agregar %(qty)s de «%(product)s».\n"
                    "A la mano en el almacén %(wh)s: %(available)s %(uom)s.",
                    qty=line.product_uom_qty,
                    product=line.product_id.display_name,
                    wh=line.order_id.warehouse_id.display_name or "—",
                    available=max_qty,
                    uom=line.product_uom_id.name,
                ))

    @api.onchange("product_uom_qty", "product_id", "product_uom_id")
    def _onchange_warn_qty_available(self):
        if not self or not self.product_id or not self.product_id.is_storable:
            return
        if self.state in ("sale", "done", "cancel"):
            return
        if self.display_type:
            return
        max_qty = self._max_qty_in_line_uom()
        if max_qty is None:
            return
        if self.product_uom_qty > max_qty:
            self.product_uom_qty = max_qty
            return {
                "warning": {
                    "title": _("Stock insuficiente"),
                    "message": _(
                        "Solo hay %(available)s %(uom)s a la mano de «%(product)s» "
                        "en el almacén %(wh)s. La cantidad fue ajustada automáticamente.",
                        available=max_qty,
                        uom=self.product_uom_id.name,
                        product=self.product_id.display_name,
                        wh=self.order_id.warehouse_id.display_name or "—",
                    ),
                }
            }
