from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    attendance_geofence_ids = fields.One2many(
        "hr.attendance.geofence", "company_id",
        string="Geocercas de respaldo para asistencia")
