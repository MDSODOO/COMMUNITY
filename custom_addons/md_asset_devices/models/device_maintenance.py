# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeviceMaintenance(models.Model):
    _name = "device.maintenance"
    _description = "Mantenimiento de Dispositivos"
    _rec_name = "name"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fecha_programada asc, id desc'

    name = fields.Char(string="Folio", default="/", copy=False, readonly=True, tracking=True)
    device_id = fields.Many2one('device.management', string="Dispositivo", required=True, ondelete='cascade')

    # Tipo de mantenimiento
    tipo = fields.Selection([
        ('preventivo', 'Preventivo'),
        ('correctivo', 'Correctivo'),
    ], string="Tipo", required=True)

    # Cronograma
    fecha_programada = fields.Date(string="Fecha Programada", required=True)
    fecha_inicio = fields.Date(string="Fecha de Inicio")
    fecha_fin = fields.Date(string="Fecha de Finalización")

    # Descripción
    descripcion = fields.Text(string="Descripción del Mantenimiento")
    observaciones = fields.Text(string="Observaciones")

    # Estado
    estado = fields.Selection([
        ('draft', 'Borrador'),
        ('scheduled', 'Programado'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
    ], string="Estado", default='draft', tracking=True)

    # Asignación
    tecnico_asignado = fields.Many2one('hr.employee', string="Técnico Asignado")

    # Costo
    costo_mano_obra = fields.Float(string="Costo Mano de Obra", digits=(10, 2))
    costo_repuestos = fields.Float(string="Costo Repuestos", digits=(10, 2))
    costo_total = fields.Float(string="Costo Total", compute='_compute_costo_total', digits=(10, 2))

    # Próximo mantenimiento
    proximo_mantenimiento = fields.Date(string="Próximo Mantenimiento")

    # ─── COMPUTES ───────────────────────────────────────────
    @api.depends('costo_mano_obra', 'costo_repuestos')
    def _compute_costo_total(self):
        for maint in self:
            maint.costo_total = (maint.costo_mano_obra or 0) + (maint.costo_repuestos or 0)

    # ─── VALIDACIONES / VALIDATIONS ─────────────────────────
    @api.constrains('device_id')
    def _check_device_not_retired(self):
        for maint in self:
            if maint.device_id.state == 'retired':
                raise ValidationError(_(
                    "No se puede programar un mantenimiento para '%(device)s': "
                    "está Fuera de servicio."
                ) % {'device': maint.device_id.nombre_dispositivo})

    # ─── ACTIONS ────────────────────────────────────────────
    def action_confirmar(self):
        self.estado = 'scheduled'

    def action_iniciar(self):
        self.write({'estado': 'in_progress', 'fecha_inicio': fields.Date.today()})

    def action_completar(self):
        self.write({'estado': 'completed', 'fecha_fin': fields.Date.today()})
        for maint in self.filtered(
            lambda m: m.proximo_mantenimiento and m.device_id.state != 'retired'
        ):
            self.env['device.maintenance'].create({
                'device_id': maint.device_id.id,
                'tipo': maint.tipo,
                'fecha_programada': maint.proximo_mantenimiento,
                'tecnico_asignado': maint.tecnico_asignado.id if maint.tecnico_asignado else False,
                'descripcion': f'Seguimiento de: {maint.descripcion or maint.device_id.nombre_dispositivo}',
                'estado': 'draft',
            })

    def action_cancelar(self):
        self.estado = 'cancelled'

    def write(self, vals):
        devices = self.mapped('device_id')
        result = super().write(vals)
        if 'estado' in vals or 'device_id' in vals:
            (devices | self.mapped('device_id'))._sync_maintenance_state()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('device.maintenance') or '/'
        maintenances = super().create(vals_list)
        maintenances.mapped('device_id')._sync_maintenance_state()
        return maintenances

    def unlink(self):
        devices = self.mapped('device_id')
        result = super().unlink()
        devices._sync_maintenance_state()
        return result
