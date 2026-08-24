from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    biometric_credential_ids = fields.One2many(
        "hr.employee.biometric.credential", "employee_id",
        string="Credenciales biométricas (huella)")
