from odoo import models, fields, api
from odoo.addons.md_cfdi_stamping.models.cfdi_catalogos import METODO_PAGO_SELECTION


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    l10n_mx_edi_payment_policy = fields.Selection(
        METODO_PAGO_SELECTION,
        default="PUE",
    )


class SaleOrderLineInherit(models.Model):
    _inherit = "sale.order.line"

    can_edit_price = fields.Boolean(
        compute="_compute_permissions"
    )

    can_edit_tax = fields.Boolean(
        compute="_compute_permissions"
    )

    @api.depends_context("uid")
    def _compute_permissions(self):
        user = self.env.user
        for rec in self:
            rec.can_edit_price = user.has_group(
                "sale_account_custom.group_sale_edit_price"
            )
            rec.can_edit_tax = user.has_group(
                "sale_account_custom.group_sale_edit_tax"
            )