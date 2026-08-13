# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeviceInventory(models.Model):
    _name = "device.inventory"
    _description = "Inventario de Dispositivos - A la mano"
    _rec_name = "device_id"

    device_id = fields.Many2one('device.management', string="Dispositivo", required=True, ondelete='cascade')

    # Cantidad A la mano (REGLA CRÍTICA)
    cantidad_a_la_mano = fields.Integer(string="Cantidad A la mano", required=True, default=1)
    cantidad_asignada = fields.Integer(string="Cantidad Asignada", compute='_compute_cantidades')
    cantidad_dañada = fields.Integer(string="Dañadas/Perdidas", compute='_compute_cantidades')
    capacidad_asignacion = fields.Integer(string="Espacio para Asignación", compute='_compute_capacidad_asignacion')

    # Ubicación y responsabilidad
    ubicacion = fields.Char(string="Ubicación en Almacén")
    responsable = fields.Many2one('hr.employee', string="Responsable")

    # Relación con asignaciones
    assignment_ids = fields.One2many('device.assignment', 'inventory_id', string="Asignaciones")

    # Auditoría
    fecha_ultimo_inventario = fields.Date(string="Último Inventario Físico")
    observaciones = fields.Text(string="Observaciones")

    # ─── COMPUTES ───────────────────────────────────────────
    @api.depends('assignment_ids.estado')
    def _compute_cantidades(self):
        for inv in self:
            inv.cantidad_asignada = len(inv.assignment_ids.filtered(lambda a: a.estado == 'activa'))
            inv.cantidad_dañada = len(inv.assignment_ids.filtered(
                lambda a: a.estado in ('perdido', 'roto')
            ))

    @api.depends('cantidad_a_la_mano', 'cantidad_asignada')
    def _compute_capacidad_asignacion(self):
        for inv in self:
            inv.capacidad_asignacion = inv.cantidad_a_la_mano - inv.cantidad_asignada

    # ─── VALIDACIONES / VALIDATIONS ─────────────────────────
    @api.constrains('cantidad_a_la_mano')
    def _check_cantidad_a_la_mano(self):
        for inv in self:
            if inv.cantidad_a_la_mano < 0:
                raise ValidationError(_("La cantidad A la mano no puede ser negativa."))
            if inv.cantidad_asignada > inv.cantidad_a_la_mano:
                raise ValidationError(_(
                    "No puedes tener más asignaciones activas que cantidad A la mano."
                ))
