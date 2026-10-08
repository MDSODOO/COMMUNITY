from odoo import fields, models

LOCATION_SOURCE_SELECTION = [
    ("ip", "Red de sucursal (IP)"),
    ("geofence", "Geocerca (GPS)"),
    ("manual", "Sin validar / revisar"),
]


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    # selection_add es aditivo: no toca los valores existentes (kiosk,
    # systray, manual, technical, auto_check_out) del módulo core.
    in_mode = fields.Selection(
        selection_add=[("biometric", "Huella (biométrico)")],
        ondelete={"biometric": "set default"})
    out_mode = fields.Selection(
        selection_add=[("biometric", "Huella (biométrico)")],
        ondelete={"biometric": "set default"})

    in_biometric_verified = fields.Boolean(string="Huella verificada (entrada)", readonly=True)
    out_biometric_verified = fields.Boolean(string="Huella verificada (salida)", readonly=True)

    in_biometric_credential_id = fields.Many2one(
        "hr.employee.biometric.credential", string="Credencial usada (entrada)", readonly=True)
    out_biometric_credential_id = fields.Many2one(
        "hr.employee.biometric.credential", string="Credencial usada (salida)", readonly=True)

    in_location_source = fields.Selection(
        LOCATION_SOURCE_SELECTION, string="Ubicación validada (entrada)", readonly=True)
    out_location_source = fields.Selection(
        LOCATION_SOURCE_SELECTION, string="Ubicación validada (salida)", readonly=True)

    in_geofence_id = fields.Many2one(
        "hr.attendance.geofence", string="Geocerca usada (entrada)", readonly=True)
    out_geofence_id = fields.Many2one(
        "hr.attendance.geofence", string="Geocerca usada (salida)", readonly=True)
