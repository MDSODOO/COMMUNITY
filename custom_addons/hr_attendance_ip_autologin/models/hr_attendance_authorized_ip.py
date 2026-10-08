import ipaddress

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrAttendanceAuthorizedIp(models.Model):
    _name = "hr.attendance.authorized.ip"
    _description = "IP autorizada para check-in automático por sucursal"
    _rec_name = "name"

    name = fields.Char(
        string="Nombre",
        required=True,
        help="Ej. 'Router principal - MDS Cancún'.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Sucursal",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help=(
            "Sucursal a la que pertenece esta IP. En esta instancia cada "
            "res.company es una sucursal (1 compañía = 1 almacén)."
        ),
    )
    ip_address = fields.Char(
        string="Dirección IP",
        required=True,
        help="IP única (189.203.10.5) o rango CIDR (189.203.10.0/24, también IPv6).",
    )
    active = fields.Boolean(string="Activo", default=True)

    @api.constrains("ip_address")
    def _check_ip_address(self):
        for rec in self:
            try:
                ipaddress.ip_network(rec.ip_address.strip(), strict=False)
            except ValueError as exc:
                raise ValidationError(
                    "'%s' no es una IP ni un rango CIDR válido (ej. 189.203.10.5 "
                    "o 189.203.10.0/24)." % rec.ip_address
                ) from exc

    def _matches(self, remote_ip):
        """True si remote_ip cae dentro de este registro (IP única o CIDR)."""
        self.ensure_one()
        try:
            network = ipaddress.ip_network(self.ip_address.strip(), strict=False)
            return ipaddress.ip_address(remote_ip) in network
        except ValueError:
            return False
