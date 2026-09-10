import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

APPROVAL_REQUIRED_TYPES = ("internal",)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    x_requires_approval = fields.Boolean(
        string="Requiere aprobación",
        compute="_compute_x_requires_approval",
        store=True,
        help="True solo para transferencias internas entre almacenes "
        "distintos (no aplica a movimientos dentro de la misma sucursal).",
    )
    x_approval_state = fields.Selection(
        [
            ("not_required", "No requiere aprobación"),
            ("evidence_pending", "Evidencia pendiente"),
            ("to_approve", "Por aprobar"),
            ("approved", "Aprobado"),
            ("rejected", "Rechazado"),
        ],
        string="Estado de aprobación",
        default="not_required",
        copy=False,
        tracking=True,
    )
    x_evidence_product_ids = fields.Many2many(
        "ir.attachment",
        "md_transfer_evidence_product_rel",
        "picking_id",
        "attachment_id",
        string="Evidencia: estado físico del producto",
        help="Fotos obligatorias del estado físico de empaques/blíster y "
        "fechas de caducidad visibles, antes de solicitar aprobación.",
    )
    x_evidence_package_ids = fields.Many2many(
        "ir.attachment",
        "md_transfer_evidence_package_rel",
        "picking_id",
        "attachment_id",
        string="Evidencia: empaque final sellado",
        help="Fotos obligatorias de la caja cerrada, fleje/cinta de "
        "seguridad y folio visible, antes de solicitar aprobación.",
    )
    x_approval_user_id = fields.Many2one(
        "res.users",
        string="Aprobado por",
        readonly=True,
        copy=False,
    )
    x_approval_date = fields.Datetime(
        string="Fecha de aprobación",
        readonly=True,
        copy=False,
    )
    x_rejection_reason = fields.Text(
        string="Motivo de rechazo",
        copy=False,
    )

    @api.depends("picking_type_id.code", "location_id.warehouse_id", "location_dest_id.warehouse_id")
    def _compute_x_requires_approval(self):
        for picking in self:
            same_warehouse = (
                picking.location_id.warehouse_id
                and picking.location_id.warehouse_id == picking.location_dest_id.warehouse_id
            )
            picking.x_requires_approval = bool(
                picking.picking_type_id.code in APPROVAL_REQUIRED_TYPES
                and picking.location_dest_id.warehouse_id
                and not same_warehouse
            )

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        for picking in pickings:
            if picking.x_requires_approval and picking.x_approval_state == "not_required":
                picking.x_approval_state = "evidence_pending"
        return pickings

    def action_request_approval(self):
        for picking in self:
            if not picking.x_requires_approval:
                raise UserError(_("Este traslado no requiere aprobación."))
            if not picking.x_evidence_product_ids:
                raise UserError(
                    _("Adjunta al menos una foto del estado físico del producto antes de solicitar aprobación.")
                )
            if not picking.x_evidence_package_ids:
                raise UserError(
                    _("Adjunta al menos una foto del empaque sellado antes de solicitar aprobación.")
                )
            picking.x_approval_state = "to_approve"
            picking._notify_approver()
            picking._dispatch_n8n_event("to_approve")

    def action_approve_transfer(self):
        approver_group = self.env.ref(
            "md_stock_transfer_approval.group_transfer_approver", raise_if_not_found=False
        )
        for picking in self:
            if approver_group and approver_group not in self.env.user.groups_id:
                raise UserError(_("No tienes permiso para aprobar traslados internos."))
            if picking.x_approval_state != "to_approve":
                raise UserError(_("El traslado %s no está pendiente de aprobación.") % picking.name)
            picking.write(
                {
                    "x_approval_state": "approved",
                    "x_approval_user_id": self.env.user.id,
                    "x_approval_date": fields.Datetime.now(),
                }
            )
            picking.message_post(body=_("Traslado aprobado por %s.") % self.env.user.name)
            picking._dispatch_n8n_event("approved")

    def action_reject_transfer(self):
        for picking in self:
            if picking.x_approval_state != "to_approve":
                raise UserError(_("El traslado %s no está pendiente de aprobación.") % picking.name)
            if not picking.x_rejection_reason:
                raise UserError(_("Indica el motivo de rechazo antes de continuar."))
            picking.x_approval_state = "rejected"
            picking.message_post(
                body=_("Traslado rechazado por %s. Motivo: %s")
                % (self.env.user.name, picking.x_rejection_reason)
            )
            picking._dispatch_n8n_event("rejected")

    def button_validate(self):
        blocked = self.filtered(
            lambda p: p.x_requires_approval and p.x_approval_state != "approved"
        )
        if blocked:
            raise UserError(
                _(
                    "No se puede validar el traslado %s: falta aprobación "
                    "(estado actual: %s). Sube la evidencia y solicita "
                    "aprobación primero."
                )
                % (blocked[0].name, blocked[0].x_approval_state)
            )
        return super().button_validate()

    def _get_approval_threshold(self):
        param = self.env["ir.config_parameter"].sudo().get_param(
            "md_stock_transfer_approval.escalation_amount", default="5000.0"
        )
        try:
            return float(param)
        except ValueError:
            return 5000.0

    def _notify_approver(self):
        self.ensure_one()
        dest_warehouse = self.location_dest_id.warehouse_id
        approver = dest_warehouse.x_transfer_approver_id
        activity_vals = {
            "res_model_id": self.env["ir.model"]._get_id("stock.picking"),
            "res_id": self.id,
            "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
            "summary": _("Aprobar traslado interno %s") % self.name,
            "note": _(
                "Traslado %s hacia %s requiere aprobación con evidencia "
                "fotográfica ya adjunta."
            )
            % (self.name, dest_warehouse.name),
        }
        if approver:
            activity_vals["user_id"] = approver.id
            self.activity_schedule(**activity_vals)
        else:
            group = self.env.ref(
                "md_stock_transfer_approval.group_transfer_approver", raise_if_not_found=False
            )
            if not group:
                return
            for user in group.users:
                self.activity_schedule(**{**activity_vals, "user_id": user.id})

        estimated_value = sum(
            self.move_ids.mapped(lambda m: m.product_id.standard_price * m.product_uom_qty)
        )
        if estimated_value > self._get_approval_threshold():
            escalation_email = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("md_stock_transfer_approval.escalation_email")
            )
            if escalation_email:
                self.message_subscribe(partner_ids=[])
                self.message_post(
                    body=_(
                        "Traslado de alto valor estimado (%.2f) escalado a "
                        "Operaciones Centrales (%s)."
                    )
                    % (estimated_value, escalation_email)
                )

    def _dispatch_n8n_event(self, event_type):
        """Best-effort: nunca bloquea la transacción de inventario si n8n
        no responde. Errores se registran en el log y en el chatter, no se
        propagan como excepción."""
        webhook_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("md_stock_transfer_approval.n8n_webhook_url")
        )
        if not webhook_url:
            return
        payload = {
            "event": event_type,
            "picking_id": self.id,
            "picking_name": self.name,
            "origin_warehouse": self.location_id.warehouse_id.name,
            "dest_warehouse": self.location_dest_id.warehouse_id.name,
            "approval_state": self.x_approval_state,
        }
        try:
            requests.post(webhook_url, json=payload, timeout=5)
        except requests.RequestException as exc:
            _logger.warning(
                "md_stock_transfer_approval: fallo al notificar n8n para picking %s: %s",
                self.name,
                exc,
            )
