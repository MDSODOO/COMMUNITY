# -*- coding: utf-8 -*-
import json
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

DEFAULT_BORDER_ZONE_ZIP_RANGES = [
    (21000, 22999),   # Baja California
    (83000, 85999),   # Sonora
    (31700, 32999),   # Chihuahua
    (26000, 26999),   # Coahuila
    (88000, 88999),   # Tamaulipas
    (77000, 77999),   # Quintana Roo (Chetumal)
    (29000, 30999),   # Chiapas
    (86900, 86999),   # Tabasco
    (24700, 24999),   # Campeche
]


def _is_zip_in_border_zone(zip_code, ranges=None):
    """Comprueba si un código postal cae en un rango de Franja Fronteriza.

    Args:
        zip_code: str o int, código postal a validar.
        ranges: list de tuplas (min, max) de rangos fronterizos. Si es None, usa DEFAULT_BORDER_ZONE_ZIP_RANGES.

    Returns:
        bool: True si el CP cae dentro de algún rango, False en otro caso (incluyendo si no es numérico).
    """
    if ranges is None:
        ranges = DEFAULT_BORDER_ZONE_ZIP_RANGES

    if not zip_code:
        return False

    try:
        zip_int = int(str(zip_code).strip())
    except (ValueError, TypeError):
        return False

    return any(low <= zip_int <= high for low, high in ranges)


class AccountFiscalPositionInherit(models.Model):
    _inherit = "account.fiscal.position"

    @api.model
    def _get_fiscal_position(self, partner, delivery=None):
        """Calcula la posición fiscal, anulando la posición fronteriza si la sucursal emisora no es fronteriza.

        Regla: El Lugar de Expedición (CP de la compañía/sucursal) dicta las reglas fiscales, no el
        domicilio del receptor. Si la sucursal emisora no es fronteriza, se ignora la posición fiscal
        fronteriza del cliente y se devuelve None para que apliquen los impuestos nacionales estándar.
        """
        fiscal_position = super()._get_fiscal_position(partner, delivery)

        if not fiscal_position:
            return fiscal_position

        company = self.env.company

        if not company.country_id or company.country_id.code != 'MX':
            return fiscal_position

        company_zip = company.zip
        if not company_zip or _is_zip_in_border_zone(company_zip):
            return fiscal_position

        if not (fiscal_position.zip_from or fiscal_position.zip_to):
            return fiscal_position

        _logger.info(
            "Anulando posición fiscal fronteriza '%s' porque la sucursal emisora "
            "CP %s no está en zona fronteriza. Se aplicarán impuestos nacionales estándar.",
            fiscal_position.name,
            company_zip,
        )
        return self.env['account.fiscal.position']
