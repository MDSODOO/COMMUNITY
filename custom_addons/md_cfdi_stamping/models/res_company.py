import base64

from odoo import fields, models, _
from odoo.exceptions import UserError
from .cfdi_catalogos import REGIMEN_FISCAL_SELECTION


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_mx_regimen_fiscal = fields.Selection(
        REGIMEN_FISCAL_SELECTION,
        string='Régimen Fiscal (SAT)',
    )
    l10n_mx_csd_certificate = fields.Binary(
        string='CSD - Certificado (.cer)',
        attachment=True,
        groups='account.group_account_manager',
    )
    l10n_mx_csd_certificate_filename = fields.Char(string='Nombre del archivo .cer')
    l10n_mx_csd_key = fields.Binary(
        string='CSD - Llave privada (.key)',
        attachment=True,
        groups='account.group_account_manager',
    )
    l10n_mx_csd_key_filename = fields.Char(string='Nombre del archivo .key')
    l10n_mx_csd_password = fields.Char(
        string='CSD - Contraseña',
        groups='account.group_account_manager',
    )
    l10n_mx_pac_username = fields.Char(
        string='PAC - Usuario',
        groups='account.group_account_manager',
    )
    l10n_mx_pac_password = fields.Char(
        string='PAC - Contraseña',
        groups='account.group_account_manager',
    )
    l10n_mx_pac_test_mode = fields.Boolean(
        string='PAC en modo de pruebas',
        default=True,
        help='Mientras esté activo, el timbrado se hace contra el ambiente '
             'de pruebas del PAC (no genera CFDIs reales ante el SAT).',
    )

    def _l10n_mx_get_signer(self):
        from satcfdi.models import Signer

        self.ensure_one()
        if not (self.l10n_mx_csd_certificate and self.l10n_mx_csd_key and self.l10n_mx_csd_password):
            raise UserError(_(
                'Falta configurar el CSD (certificado, llave y contraseña) en la '
                'compañía %s antes de generar el CFDI.'
            ) % self.name)
        return Signer.load(
            certificate=base64.b64decode(self.l10n_mx_csd_certificate),
            key=base64.b64decode(self.l10n_mx_csd_key),
            password=self.l10n_mx_csd_password,
        )
