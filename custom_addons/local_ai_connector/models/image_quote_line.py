# -*- coding: utf-8 -*-
from odoo import fields, models


class LocalAiImageQuoteLine(models.Model):
    _name = "local.ai.image.quote.line"
    _description = (
        "Un renglon extraido de una imagen de cotizacion, con su intento de "
        "match de producto. NUNCA se convierte en linea de sale.order sin "
        "que 'confirmed' este en True -- puesto explicitamente por staff en "
        "la revision, jamas por el modelo ni por el matching automatico "
        "(ver action_create_quotation en image_quote_request.py)."
    )
    _order = "request_id, sequence, id"

    request_id = fields.Many2one(
        "local.ai.image.quote.request", string="Solicitud",
        required=True, ondelete="cascade", index=True,
    )
    source_image_id = fields.Many2one(
        "local.ai.image.quote.image", string="Imagen de origen", ondelete="set null",
    )
    sequence = fields.Integer(default=10)

    text_detected = fields.Char(string="Texto detectado", required=True)
    quantity_detected = fields.Float(string="Cantidad detectada")

    product_id = fields.Many2one("product.product", string="Producto sugerido/asignado")
    match_confidence = fields.Float(string="Confianza del match", readonly=True)
    match_method = fields.Char(string="Método de match", readonly=True)
    match_status = fields.Selection([
        ("matched", "Coincidencia encontrada"),
        ("not_found", "Sin coincidencia"),
    ], string="Estado del match", readonly=True)

    confirmed = fields.Boolean(
        string="Confirmado por staff", default=False,
        help="Solo las líneas confirmadas se incluyen al crear la cotización.",
    )
