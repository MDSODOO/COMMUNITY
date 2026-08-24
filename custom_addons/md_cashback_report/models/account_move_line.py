# -*- coding: utf-8 -*-
from odoo import api, models


class AccountMoveLine(models.Model):
    # Aplica automáticamente el % de descuento del esquema 2% + cashback 5%
    # en líneas de producto de facturas de cliente (out_invoice) cuando el
    # partner tiene x_cashback_split_scheme=True: 0% si el producto está en
    # su lista de exclusión (x_cashback_excluded_product_ids), 2% en caso
    # contrario. Corre a nivel de ORM (create/write), no de onchange, para
    # que aplique sin importar el origen de la línea (RPC/RPA, UI, import).
    # Solo toca líneas de facturas en borrador; una vez posteada, Odoo ya
    # protege esos campos por su cuenta.
    _inherit = 'account.move.line'

    def _get_cashback_scheme_discount(self):
        self.ensure_one()
        move = self.move_id
        if (
            move.move_type != 'out_invoice'
            or self.display_type != 'product'
            or not self.product_id
            or not move.partner_id.x_cashback_split_scheme
        ):
            return None
        excluded = move.partner_id.x_cashback_excluded_product_ids
        return 0.0 if self.product_id in excluded else 2.0

    def _apply_cashback_scheme_discount(self):
        for line in self:
            if line.move_id.state != 'draft':
                continue
            discount = line._get_cashback_scheme_discount()
            if discount is not None and line.discount != discount:
                line.discount = discount

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._apply_cashback_scheme_discount()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if vals.keys() & {'product_id', 'move_id', 'display_type'}:
            self._apply_cashback_scheme_discount()
        return res
