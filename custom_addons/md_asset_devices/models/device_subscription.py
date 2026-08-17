# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date


class DeviceSubscription(models.Model):
    _name = "device.subscription"
    _description = "Suscripciones y Licencias del Dispositivo"
    _rec_name = "nombre_servicio"
    _inherit = ['mail.thread']
    _order = 'fecha_vencimiento asc, id desc'

    device_id = fields.Many2one('device.management', string="Dispositivo", required=True, ondelete='cascade')

    # Tipo
    tipo = fields.Selection([
        ('software', 'Software/Licencia'),
        ('antivirus', 'Antivirus'),
        ('backup', 'Servicio de Backup'),
        ('soporte', 'Soporte Técnico'),
        ('otro', 'Otro'),
    ], string="Tipo de Suscripción", required=True)

    nombre_servicio = fields.Char(string="Nombre del Servicio", required=True)
    descripcion = fields.Text(string="Descripción")
    url_acceso = fields.Char(string="URL de Acceso")

    # Credenciales (solo para admin)
    usuario = fields.Char(
        string="Usuario",
        groups="md_asset_devices.device_management_admin_group"
    )
    contrasena = fields.Char(
        string="Contraseña",
        groups="md_asset_devices.device_management_admin_group"
    )

    # Renovación
    fecha_inicio = fields.Date(string="Fecha de Inicio")
    fecha_vencimiento = fields.Date(string="Fecha de Vencimiento", required=True)
    periodo_renovacion = fields.Selection([
        ('mensual', 'Mensual'),
        ('anual', 'Anual'),
        ('bienal', 'Bienal'),
    ], string="Período de Renovación")

    # Costos
    costo_anual = fields.Float(string="Costo Anual", digits=(10, 2))

    # Estado
    estado = fields.Selection([
        ('activo', 'Activo'),
        ('proximo_vencer', 'Próximo a Vencer'),
        ('vencido', 'Vencido'),
        ('cancelado', 'Cancelado'),
    ], string="Estado", compute='_compute_estado', store=True)

    # Alerta visual
    dias_para_vencer = fields.Integer(
        string="Días para Vencer",
        compute='_compute_dias_para_vencer'
    )

    # ─── COMPUTES ───────────────────────────────────────────
    @api.depends('fecha_vencimiento')
    def _compute_estado(self):
        today = date.today()
        for sub in self:
            if not sub.fecha_vencimiento:
                sub.estado = 'activo'
            elif sub.fecha_vencimiento < today:
                sub.estado = 'vencido'
            elif (sub.fecha_vencimiento - today).days <= 30:
                sub.estado = 'proximo_vencer'
            else:
                sub.estado = 'activo'

    @api.depends('fecha_vencimiento')
    def _compute_dias_para_vencer(self):
        today = date.today()
        for sub in self:
            if sub.fecha_vencimiento:
                delta = (sub.fecha_vencimiento - today).days
                sub.dias_para_vencer = max(-999, delta)
            else:
                sub.dias_para_vencer = 0
