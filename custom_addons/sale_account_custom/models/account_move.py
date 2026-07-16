from odoo import _, models, fields, api
from odoo.exceptions import AccessError


PAYMENT_GROUP = "sale_account_custom.group_account_payment"
DRAFT_GROUP = "sale_account_custom.group_account_draft"


class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    can_pay = fields.Boolean(
        compute="_compute_permissions"
    )

    can_draft = fields.Boolean(
        compute="_compute_permissions"
    )

    md_authorization_check_number = fields.Char(
        string="Número de autorización o cheque",
        copy=False,
    )

    md_payment_method_display = fields.Char(
        string="Método de pago mostrado",
        compute="_compute_vendor_payment_list_values",
    )

    md_authorization_check_display = fields.Char(
        string="Número de autorización o cheque (Vista)",
        compute="_compute_vendor_payment_list_values",
    )

    @api.depends(
        "md_authorization_check_number",
        "l10n_mx_forma_pago",
        "l10n_mx_metodo_pago",
        "payment_reference",
        "ref",
    )
    def _compute_vendor_payment_list_values(self):
        # Reemplazo Community (md_cfdi_stamping) de l10n_mx_edi_payment_method_id
        # / l10n_mx_edi_payment_policy, que solo existen con el módulo Enterprise.
        payment_method_field = "l10n_mx_forma_pago"
        payment_policy_field = "l10n_mx_metodo_pago"

        for move in self:
            payment_label = ""
            payment_method = (
                move[payment_method_field]
                if payment_method_field in move._fields
                else False
            )
            if payment_method:
                selection = move._fields[payment_method_field].selection
                method_selection = dict(selection) if isinstance(selection, list) else {}
                payment_label = method_selection.get(payment_method, payment_method)

            payment_policy = (
                move[payment_policy_field]
                if payment_policy_field in move._fields
                else False
            )
            if not payment_label and payment_policy:
                selection = move._fields[payment_policy_field].selection
                policy_selection = dict(selection) if isinstance(selection, list) else {}
                payment_label = policy_selection.get(payment_policy, payment_policy)

            move.md_payment_method_display = payment_label
            move.md_authorization_check_display = (
                move.md_authorization_check_number
                or move.payment_reference
                or move.ref
                or ""
            )

    @api.depends_context("uid")
    def _compute_permissions(self):
        user = self.env.user
        for rec in self:
            rec.can_pay = user.has_group(PAYMENT_GROUP)
            rec.can_draft = user.has_group(DRAFT_GROUP)

    def _check_financial_action_group(self, group_xmlid, action_label):
        if not self.env.user.has_group(group_xmlid):
            raise AccessError(_(
                "No tiene permisos para %(action)s en facturas.",
                action=action_label,
            ))

    def action_register_payment(self):
        self._check_financial_action_group(
            PAYMENT_GROUP,
            _("registrar pagos"),
        )
        return super().action_register_payment()

    def button_draft(self):
        self._check_financial_action_group(
            DRAFT_GROUP,
            _("restablecer a borrador"),
        )
        return super().button_draft()
