# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class DeviceTodo(models.Model):
    _name = "device.todo"
    _description = "Tareas y Actividades del Dispositivo"
    _rec_name = "titulo"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fecha_vencimiento asc, prioridad desc, id desc'

    device_id = fields.Many2one('device.management', string="Dispositivo", required=True, ondelete='cascade')

    titulo = fields.Char(string="Título", required=True)
    descripcion = fields.Text(string="Descripción")

    tipo = fields.Selection([
        ('tarea', 'Tarea'),
        ('recordatorio', 'Recordatorio'),
        ('evento', 'Evento'),
    ], string="Tipo")

    # Fechas
    fecha_vencimiento = fields.Date(string="Fecha de Vencimiento")
    fecha_completado = fields.Date(string="Fecha de Completación")

    # Estado
    estado = fields.Selection([
        ('todo', 'Por Hacer'),
        ('in_progress', 'En Progreso'),
        ('done', 'Completado'),
        ('cancelled', 'Cancelada'),
    ], string="Estado", default='todo', tracking=True)

    # Asignación
    asignado_a = fields.Many2one('hr.employee', string="Asignado a")
    prioridad = fields.Selection([
        ('baja', 'Baja'),
        ('normal', 'Normal'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ], string="Prioridad", default='normal')

    # ─── ACTIONS ────────────────────────────────────────────
    def action_marcar_done(self):
        self.write({
            'estado': 'done',
            'fecha_completado': fields.Date.today(),
        })

    def action_marcar_in_progress(self):
        self.estado = 'in_progress'

    def action_marcar_todo(self):
        self.estado = 'todo'

    def action_cancelar(self):
        self.estado = 'cancelled'
