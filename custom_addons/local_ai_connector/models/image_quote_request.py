# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class LocalAiImageQuoteRequest(models.Model):
    _name = "local.ai.image.quote.request"
    _description = (
        "Solicitud de cotizacion por imagen. Cola asincrona -- cada imagen "
        "tarda 90-240s en procesarse (medido con qwen2.5vl:7b en CPU, ver "
        "docs/AI_MODEL_ODOO_CONFIG.md §9.2), asi que no se procesa en la "
        "misma request HTTP que la subida. Un cron (ver "
        "services/image_quote_processor.py) recoge las solicitudes "
        "'pending' una por una. Dos canales de entrada, ver origin_channel: "
        "el endpoint publico (/ai/quote_from_image, cliente sube la foto el "
        "mismo) y el interno (/ai/quote_from_image/staff, un empleado "
        "arrastra una foto recibida por WhatsApp -- la mayoria de las "
        "cotizaciones llegan asi, no por el formulario publico)."
    )
    _order = "create_date desc"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Referencia", default="Nueva", copy=False)
    state = fields.Selection([
        ("pending", "Pendiente de procesar"),
        ("processing", "Procesando"),
        ("ready_for_review", "Lista para revisión"),
        ("reviewed", "Cotización creada"),
        ("error", "Error"),
    ], string="Estado", default="pending", required=True, tracking=True, index=True)

    origin_channel = fields.Selection([
        ("public_web", "Sitio web público"),
        ("internal_staff", "Interna (staff, WhatsApp)"),
    ], string="Canal de origen", default="public_web", required=True, index=True)

    customer_name = fields.Char(string="Nombre del cliente", required=True)
    # Sin required=True: la via interna (WhatsApp) casi nunca trae correo,
    # solo nombre + telefono -- ver _check_contact_info mas abajo, que exige
    # al menos uno de los dos en vez de forzar el correo especificamente.
    customer_email = fields.Char(string="Correo del cliente")
    customer_phone = fields.Char(string="Teléfono del cliente")
    ip_address = fields.Char(string="Dirección IP de origen")

    @api.constrains("customer_email", "customer_phone")
    def _check_contact_info(self):
        for request in self:
            if not request.customer_email and not request.customer_phone:
                raise ValidationError(
                    "Se necesita al menos un dato de contacto del cliente "
                    "(correo o teléfono)."
                )

    image_ids = fields.One2many(
        "local.ai.image.quote.image", "request_id", string="Imágenes",
    )
    line_ids = fields.One2many(
        "local.ai.image.quote.line", "request_id", string="Renglones detectados",
    )
    sale_order_id = fields.Many2one("sale.order", string="Cotización creada", readonly=True)
    error_message = fields.Text(string="Detalle del error")

    @api.model
    def _cron_process_pending(self):
        """Llamado por el cron (data/image_quote_cron.xml). Procesa como
        maximo 1 solicitud por ejecucion a proposito -- ver la nota de
        concurrencia en services/ollama_client.py sobre por que la
        serializacion real depende del propio locking de ir.cron."""
        from ..services.image_quote_processor import process_next_pending_request
        process_next_pending_request(self.env)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nueva") == "Nueva":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "local.ai.image.quote.request"
                ) or "AIQ-Nueva"
        return super().create(vals_list)

    def action_create_quotation(self):
        """Crea el sale.order a partir de las lineas confirmadas por staff.

        Solo lineas con product_id asignado Y confirmed=True se incluyen --
        nunca se incluye una linea sin revision humana explicita, sin
        importar que tan alta haya sido la confianza del matching
        automatico (regla de gobernanza de todo este modulo: el LLM/matching
        automatico nunca es la fuente de verdad final, ver
        docs/AI_MODEL_ODOO_CONFIG.md §6.3).
        """
        self.ensure_one()
        if self.state not in ("ready_for_review", "error"):
            raise UserError("Esta solicitud todavía no está lista para revisión.")

        confirmed_lines = self.line_ids.filtered(lambda l: l.confirmed and l.product_id)
        if not confirmed_lines:
            raise UserError(
                "No hay ningún renglón confirmado con producto asignado. "
                "Revisa y confirma al menos una línea antes de crear la cotización."
            )

        # Busca primero por correo (identificador mas confiable cuando
        # existe); si no hay correo -- caso comun en la via interna, cliente
        # solo identificado por WhatsApp -- busca por telefono. Ninguno de
        # los dos es unico a nivel de base de datos, por lo que "limit=1"
        # puede no ser el mismo partner en dos solicitudes distintas del
        # mismo cliente; aceptable para este flujo (staff revisa el partner
        # asignado en el sale.order resultante antes de enviarlo).
        partner = self.env["res.partner"].sudo()
        if self.customer_email:
            partner = partner.search([("email", "=ilike", self.customer_email)], limit=1)
        if not partner and self.customer_phone:
            partner = self.env["res.partner"].sudo().search(
                [("phone", "=", self.customer_phone)], limit=1
            )
        if not partner:
            partner = self.env["res.partner"].sudo().create({
                "name": self.customer_name,
                "email": self.customer_email,
                "phone": self.customer_phone,
            })

        order_lines = []
        for line in confirmed_lines:
            product = line.product_id
            order_lines.append((0, 0, {
                "product_id": product.id,
                "name": product.get_product_multiline_description_sale() if hasattr(
                    product, "get_product_multiline_description_sale"
                ) else product.name,
                "product_uom_qty": line.quantity_detected or 1.0,
                "price_unit": product.list_price,
                "tax_ids": [(6, 0, product.taxes_id.filtered(
                    lambda t: t.company_id == self.env.company
                ).ids)],
            }))

        order = self.env["sale.order"].sudo().create({
            "partner_id": partner.id,
            "origin": self.name,
            "order_line": order_lines,
        })
        order.message_post(
            body=(
                "Cotización generada desde una imagen enviada por el cliente "
                "(%s), con revisión y confirmación de staff línea por línea. "
                "Solicitud: %s"
            ) % (self.customer_email, self.name)
        )

        self.write({"state": "reviewed", "sale_order_id": order.id})
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": order.id,
            "view_mode": "form",
            "target": "current",
        }
