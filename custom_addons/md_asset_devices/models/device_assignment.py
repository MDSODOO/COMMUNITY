# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeviceAssignment(models.Model):
    _name = "device.assignment"
    _description = "Asignación de Dispositivo a Usuario"
    _rec_name = "usuario_asignado"
    _inherit = ['mail.thread']

    device_id = fields.Many2one('device.management', string="Dispositivo", required=True, ondelete='cascade')
    inventory_id = fields.Many2one('device.inventory', string="Inventario", ondelete='cascade')
    usuario_asignado = fields.Many2one('hr.employee', string="Usuario Asignado", required=True, ondelete='restrict')

    fecha_asignacion = fields.Date(string="Fecha de Asignación", required=True, default=fields.Date.today)
    fecha_devolucion = fields.Date(string="Fecha de Devolución")

    estado = fields.Selection([
        ('activa', 'Activa'),
        ('devuelto', 'Devuelto'),
        ('perdido', 'Perdido'),
        ('roto', 'Roto'),
    ], string="Estado", required=True, default='activa', tracking=True)

    observaciones = fields.Text(string="Observaciones")

    @api.onchange('estado')
    def _onchange_estado(self):
        if self.estado == 'devuelto' and not self.fecha_devolucion:
            self.fecha_devolucion = fields.Date.today()

    @api.onchange('inventory_id')
    def _onchange_inventory_id(self):
        if self.inventory_id:
            self.device_id = self.inventory_id.device_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            device_id = vals.get('device_id')
            inventory_id = vals.get('inventory_id')
            if inventory_id and not device_id:
                vals['device_id'] = self.env['device.inventory'].browse(inventory_id).device_id.id
                device_id = vals['device_id']
            # Auto-create inventory line if device has none
            if device_id and not inventory_id:
                device = self.env['device.management'].browse(device_id)
                inv = device.inventory_ids[:1]
                if not inv:
                    inv = self.env['device.inventory'].create({
                        'device_id': device_id,
                        'cantidad_a_la_mano': 1,
                    })
                vals['inventory_id'] = inv.id
        assignments = super().create(vals_list)
        assignments.mapped('device_id')._sync_assignment_summary()
        return assignments

    def write(self, vals):
        devices = self.mapped('device_id')
        if vals.get('inventory_id') and not vals.get('device_id'):
            vals = dict(vals)
            vals['device_id'] = self.env['device.inventory'].browse(vals['inventory_id']).device_id.id
        result = super().write(vals)
        (devices | self.mapped('device_id'))._sync_assignment_summary()
        return result

    def unlink(self):
        devices = self.mapped('device_id')
        result = super().unlink()
        devices._sync_assignment_summary()
        return result

    # ─── VALIDACIONES / VALIDATIONS ─────────────────────────
    @api.constrains('device_id', 'inventory_id')
    def _check_device_inventory_match(self):
        for assignment in self:
            if (
                assignment.device_id
                and assignment.inventory_id
                and assignment.inventory_id.device_id != assignment.device_id
            ):
                raise ValidationError(_(
                    "El inventario seleccionado debe pertenecer al mismo dispositivo."
                ))

    @api.constrains('inventory_id', 'estado')
    def _check_inventory_capacity(self):
        for assignment in self.filtered(lambda a: a.estado == 'activa' and a.inventory_id):
            active_count = self.search_count([
                ('inventory_id', '=', assignment.inventory_id.id),
                ('estado', '=', 'activa'),
            ])
            if active_count > assignment.inventory_id.cantidad_a_la_mano:
                raise ValidationError(_(
                    "No puedes asignar más unidades que la cantidad A la mano. "
                    "Actualiza el inventario antes de agregar más asignaciones."
                ))
