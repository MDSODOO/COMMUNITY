from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    attendance_authorized_ip_ids = fields.One2many(
        "hr.attendance.authorized.ip",
        "company_id",
        string="IPs autorizadas de asistencia",
    )
