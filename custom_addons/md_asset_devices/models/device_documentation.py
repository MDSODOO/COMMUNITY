# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeviceDocumentation(models.Model):
    _name = "device.documentation"
    _description = "Documentación del Dispositivo"
    _rec_name = "nombre_documento"

    device_id = fields.Many2one('device.management', string="Dispositivo", required=True, ondelete='cascade')

    # Tipo
    tipo = fields.Selection([
        ('manual', 'Manual de Usuario'),
        ('garantia', 'Certificado de Garantía'),
        ('acta', 'Acta de Entrega'),
        ('especificaciones', 'Especificaciones Técnicas'),
        ('contrato', 'Contrato de Servicio'),
        ('otro', 'Otro'),
    ], string="Tipo de Documento", required=True)

    nombre_documento = fields.Char(string="Nombre del Documento", required=True)
    descripcion = fields.Text(string="Descripción")
    archivo = fields.Binary(string="Archivo", attachment=True)
    nombre_archivo = fields.Char(string="Nombre de Archivo")
    url_documento = fields.Char(string="URL del Documento")

    # Fechas
    fecha_documento = fields.Date(string="Fecha del Documento")
    fecha_vencimiento = fields.Date(string="Fecha de Vencimiento")

    # Estado derivado
    documento_vigente = fields.Boolean(
        string="Documento Vigente",
        compute='_compute_documento_vigente'
    )

    # ─── COMPUTES ───────────────────────────────────────────
    @api.depends('fecha_vencimiento')
    def _compute_documento_vigente(self):
        from datetime import date
        today = date.today()
        for doc in self:
            doc.documento_vigente = (
                not doc.fecha_vencimiento or doc.fecha_vencimiento >= today
            )

    # ─── VALIDACIONES ────────────────────────────────────────
    @api.constrains('archivo', 'url_documento')
    def _check_archivo_o_url(self):
        for doc in self:
            if not doc.archivo and not doc.url_documento:
                from odoo.exceptions import ValidationError
                raise ValidationError(
                    "Debe adjuntar un archivo o indicar una URL del documento."
                )
