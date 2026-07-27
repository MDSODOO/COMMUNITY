# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LocalAiQueryLog(models.Model):
    _name = "local.ai.query.log"
    _description = (
        "Auditoria de consultas al copiloto de IA local: quien pregunto, "
        "que version de prompt se uso, y que respondio Odoo (no solo el "
        "modelo) -- mismo principio de auditabilidad que ya rige el resto "
        "del proyecto (evitar registros sin origen versionado)."
    )
    _order = "create_date desc"

    user_id = fields.Many2one("res.users", string="Usuario", required=True, index=True)
    question = fields.Text(string="Pregunta", required=True)
    prompt_version = fields.Char(string="Version del prompt", required=True)
    status = fields.Selection([
        ("ok", "Resuelto"),
        ("clarify", "Requiere aclaracion"),
        ("not_found", "Producto no encontrado"),
        ("error", "Error"),
    ], string="Resultado", required=True)
    response_message = fields.Text(string="Respuesta mostrada")
    product_id = fields.Many2one("product.product", string="Producto identificado")
    raw_model_output = fields.Text(string="Salida cruda del modelo")

    @api.model
    def log_query(self, user_id, question, prompt_version, result):
        self.sudo().create({
            "user_id": user_id,
            "question": question,
            "prompt_version": prompt_version,
            "status": result.get("status"),
            "response_message": result.get("message"),
            "product_id": result.get("product_id"),
            "raw_model_output": repr(result.get("raw_model_output")),
        })
