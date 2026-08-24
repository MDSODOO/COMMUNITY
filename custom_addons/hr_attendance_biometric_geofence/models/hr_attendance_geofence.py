import math

from odoo import api, fields, models
from odoo.exceptions import ValidationError

EARTH_RADIUS_M = 6371000


class HrAttendanceGeofence(models.Model):
    _name = "hr.attendance.geofence"
    _description = "Geocerca de respaldo para check-in de asistencia (sin cobertura de IP de sucursal)"
    _rec_name = "name"

    name = fields.Char(
        string="Nombre", required=True,
        help="Ej. 'Ruta de reparto - Zona Norte Cancún'.")
    company_id = fields.Many2one(
        "res.company", string="Sucursal", required=True, index=True,
        default=lambda self: self.env.company)
    center_latitude = fields.Float(string="Latitud del centro", digits=(10, 7), required=True)
    center_longitude = fields.Float(string="Longitud del centro", digits=(10, 7), required=True)
    radius_meters = fields.Integer(string="Radio (metros)", required=True, default=150)
    active = fields.Boolean(string="Activo", default=True)

    @api.constrains("radius_meters")
    def _check_radius(self):
        for rec in self:
            if rec.radius_meters <= 0:
                raise ValidationError("El radio de la geocerca debe ser mayor a 0 metros.")

    @api.constrains("center_latitude", "center_longitude")
    def _check_coordinates(self):
        for rec in self:
            if not (-90 <= rec.center_latitude <= 90) or not (-180 <= rec.center_longitude <= 180):
                raise ValidationError("Las coordenadas del centro de la geocerca están fuera de rango.")

    def _contains(self, latitude, longitude):
        """True si (latitude, longitude) cae dentro de este círculo (Haversine)."""
        self.ensure_one()
        lat1, lon1, lat2, lon2 = map(
            math.radians, [self.center_latitude, self.center_longitude, latitude, longitude])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        distance = 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))
        return distance <= self.radius_meters

    @api.model
    def _find_matching(self, company, latitude, longitude):
        """Primera geocerca activa de `company` que contenga el punto dado,
        o recordset vacío si ninguna coincide."""
        geofences = self.search([("company_id", "=", company.id), ("active", "=", True)])
        return geofences.filtered(lambda g: g._contains(latitude, longitude))[:1]
