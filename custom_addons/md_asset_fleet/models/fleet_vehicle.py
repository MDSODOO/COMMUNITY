# -*- coding: utf-8 -*-
from odoo import api, fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado Asignado",
        tracking=True,
        help="Empleado de Medicine Depot responsable del vehículo. "
             "Sincroniza automáticamente el Conductor (driver_id) con su contacto de trabajo.",
    )

    @api.onchange("employee_id")
    def _onchange_employee_id_sync_driver(self):
        for vehicle in self:
            vehicle.driver_id = vehicle.employee_id.work_contact_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("employee_id") and not vals.get("driver_id"):
                employee = self.env["hr.employee"].browse(vals["employee_id"])
                if employee.work_contact_id:
                    vals["driver_id"] = employee.work_contact_id.id
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("employee_id") and "driver_id" not in vals:
            employee = self.env["hr.employee"].browse(vals["employee_id"])
            if employee.work_contact_id:
                vals = {**vals, "driver_id": employee.work_contact_id.id}
        return super().write(vals)
