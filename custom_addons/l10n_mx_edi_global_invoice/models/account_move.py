import logging

_logger = logging.getLogger(__name__)

from odoo import Command, fields, models


class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    is_global_invoice = fields.Boolean(string="Es una factura global", default=False)
    md_cancelled_pos_order_ids = fields.Many2many(
        "pos.order",
        "account_move_cancelled_pos_order_rel",
        "move_id",
        "pos_order_id",
        string="Órdenes POS vinculadas antes de cancelar",
        copy=False,
        readonly=True,
    )

    def button_cancel(self):
        for rec in self:
            if rec.is_global_invoice and rec.pos_order_ids:
                historical_orders = rec.md_cancelled_pos_order_ids | rec.pos_order_ids
                rec.md_cancelled_pos_order_ids = [Command.set(historical_orders.ids)]
                rec.pos_order_ids = [(6, 0, [])]
        return super().button_cancel()

    def action_open_global_cfdi_wizard(self):
        """Abre el wizard de l10n_mx_cfdi_account para timbrar esta factura
        global como CFDI 'Público en general' (is_global_note=True).

        Reemplaza al botón de Enterprise (l10n_mx_edi_action_create_global_invoice)
        -- aquí no se reimplementa el timbrado, solo se abre el wizard ya
        existente de l10n_mx_cfdi_account con esta factura preseleccionada.
        """
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "l10n_mx_cfdi_account.cfdi_invoice_generic_create_form_action"
        )
        action["context"] = {"active_model": "account.move", "active_ids": self.ids}
        return action
