# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date


class DevicePayment(models.Model):
    _name = "device.payment"
    _description = "Pagos y Costos de Dispositivos"
    _rec_name = "descripcion"
    _inherit = ['mail.thread']
    _order = 'fecha_proxima_renovacion asc, id desc'

    device_id = fields.Many2one('device.management', string="Dispositivo", required=True, ondelete='cascade')

    # Tipo de pago
    tipo = fields.Selection([
        ('adquisicion', 'Adquisición'),
        ('renta', 'Renta Mensual'),
        ('mantenimiento', 'Mantenimiento'),
        ('repuesto', 'Repuesto'),
        ('otro', 'Otro'),
    ], string="Tipo de Pago", required=True)

    # Detalles
    descripcion = fields.Char(string="Descripción", required=True)
    monto = fields.Float(string="Monto", digits=(10, 2), required=True)

    # Cronograma
    fecha_pago = fields.Date(string="Fecha de Pago")
    fecha_proxima_renovacion = fields.Date(string="Próxima Renovación")
    periodo_pago = fields.Selection([
        ('unico', 'Único Pago'),
        ('mensual', 'Mensual'),
        ('trimestral', 'Trimestral'),
        ('anual', 'Anual'),
    ], string="Período de Pago")

    # Estado
    pagado = fields.Boolean(string="Pagado", default=False, tracking=True)
    estado = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente'),
        ('paid', 'Pagado'),
        ('overdue', 'Vencido'),
    ], string="Estado", compute='_compute_estado', store=True)

    # Integración contable
    invoice_id = fields.Many2one(
        'account.move',
        string="Factura",
        domain=[('move_type', 'in', ('out_invoice', 'in_invoice'))],
    )

    # Alerta
    dias_para_vencer = fields.Integer(
        string="Días para Vencer",
        compute='_compute_dias_para_vencer'
    )

    # ─── COMPUTES ───────────────────────────────────────────
    @api.depends('pagado', 'fecha_proxima_renovacion')
    def _compute_estado(self):
        today = date.today()
        for pago in self:
            if pago.pagado:
                pago.estado = 'paid'
            elif pago.fecha_proxima_renovacion and pago.fecha_proxima_renovacion < today:
                pago.estado = 'overdue'
            elif pago.fecha_proxima_renovacion:
                pago.estado = 'pending'
            else:
                pago.estado = 'draft'

    @api.depends('fecha_proxima_renovacion')
    def _compute_dias_para_vencer(self):
        today = date.today()
        for pago in self:
            if pago.fecha_proxima_renovacion:
                delta = (pago.fecha_proxima_renovacion - today).days
                pago.dias_para_vencer = max(-999, delta)
            else:
                pago.dias_para_vencer = 0
