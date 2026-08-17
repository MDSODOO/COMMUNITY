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
    valor_actual = fields.Float(
        string="Valor Actual Estimado",
        compute="_compute_valor_actual",
        digits=(10, 2),
        help="Depreciación lineal simple: 10% anual sobre el Purchase Value "
             "(net_car_value), contado desde la fecha de adquisición. Mismo "
             "criterio que 'Valor Actual' en Activos IT (device.management).",
    )

    @api.depends("net_car_value", "acquisition_date")
    def _compute_valor_actual(self):
        for vehicle in self:
            if not vehicle.net_car_value or not vehicle.acquisition_date:
                vehicle.valor_actual = vehicle.net_car_value or 0.0
                continue
            anos = (fields.Date.today() - vehicle.acquisition_date).days / 365.25
            depreciacion = vehicle.net_car_value * (anos * 0.10)
            vehicle.valor_actual = max(0, vehicle.net_car_value - depreciacion)

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
