# -*- coding: utf-8 -*-
from odoo import fields, models


class LocalAiImageQuoteImage(models.Model):
    _name = "local.ai.image.quote.image"
    _description = (
        "Una foto individual de una solicitud de cotizacion. Una solicitud "
        "puede traer varias -- hallazgo real (2026-07-27): un cliente puede "
        "mandar los productos en una foto y las cantidades en otra, sin "
        "relacion 1:1 evidente entre ambas (ver docs/AI_MODEL_ODOO_CONFIG.md "
        "§9.2). No se asume que una sola imagen sea siempre suficiente."
    )
    _order = "sequence, id"

    request_id = fields.Many2one(
        "local.ai.image.quote.request", string="Solicitud",
        required=True, ondelete="cascade", index=True,
    )
    sequence = fields.Integer(default=10)
    image = fields.Binary(string="Imagen", required=True, attachment=True)
    image_filename = fields.Char(string="Nombre de archivo")
    extraction_status = fields.Selection([
        ("pending", "Pendiente"),
        ("done", "Procesada"),
        ("error", "Error"),
    ], default="pending", required=True)
    extraction_raw = fields.Text(string="Respuesta cruda del modelo (auditoría)")
    error_message = fields.Text(string="Detalle del error")
