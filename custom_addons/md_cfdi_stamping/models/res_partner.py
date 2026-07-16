from odoo import fields, models
from .cfdi_catalogos import REGIMEN_FISCAL_SELECTION, USO_CFDI_SELECTION


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_mx_regimen_fiscal = fields.Selection(
        REGIMEN_FISCAL_SELECTION,
        string='Régimen Fiscal (SAT)',
    )
    l10n_mx_uso_cfdi = fields.Selection(
        USO_CFDI_SELECTION,
        string='Uso de CFDI',
        default='G03',
    )
