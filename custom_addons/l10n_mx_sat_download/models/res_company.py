# -*- coding: utf-8 -*-
"""
Extensión de res.company para gestionar la FIEL (e.firma) del SAT.

Se almacenan los archivos .cer y .key como campos Binary, y la contraseña
cifrada usando el mecanismo estándar de Odoo (ICP / fields encriptados).
"""
import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from ..lib.sat_webservice import FIEL

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    # =========================================================================
    # Campos de la FIEL
    # =========================================================================
    l10n_mx_sat_fiel_cer = fields.Binary(
        string="Certificado FIEL (.cer)",
        attachment=True,
        help="Archivo .cer de la e.firma (FIEL) emitido por el SAT.",
    )
    l10n_mx_sat_fiel_cer_filename = fields.Char(
        string="Nombre archivo .cer",
    )
    l10n_mx_sat_fiel_key = fields.Binary(
        string="Llave Privada FIEL (.key)",
        attachment=True,
        groups="base.group_system",
        help="Archivo .key de la e.firma (FIEL). Solo visible para administradores.",
    )
    l10n_mx_sat_fiel_key_filename = fields.Char(
        string="Nombre archivo .key",
    )
    l10n_mx_sat_fiel_password = fields.Char(
        string="Contraseña FIEL",
        groups="base.group_system",
        help="Contraseña de la llave privada de la FIEL.",
    )

    # Campos computados de solo lectura
    l10n_mx_sat_fiel_rfc = fields.Char(
        string="RFC (FIEL)",
        compute='_compute_fiel_info',
        store=True,
    )
    l10n_mx_sat_fiel_serial = fields.Char(
        string="No. Serie Certificado",
        compute='_compute_fiel_info',
        store=True,
    )
    l10n_mx_sat_fiel_not_after = fields.Datetime(
        string="Vigencia FIEL",
        compute='_compute_fiel_info',
        store=True,
    )
    l10n_mx_sat_fiel_valid = fields.Boolean(
        string="FIEL Válida",
        compute='_compute_fiel_info',
        store=True,
    )

    # =========================================================================
    # Compute
    # =========================================================================
    @api.depends(
        'l10n_mx_sat_fiel_cer',
        'l10n_mx_sat_fiel_key',
        'l10n_mx_sat_fiel_password',
    )
    def _compute_fiel_info(self):
        for company in self:
            company.l10n_mx_sat_fiel_rfc = False
            company.l10n_mx_sat_fiel_serial = False
            company.l10n_mx_sat_fiel_not_after = False
            company.l10n_mx_sat_fiel_valid = False

            if not (
                company.l10n_mx_sat_fiel_cer
                and company.l10n_mx_sat_fiel_key
                and company.l10n_mx_sat_fiel_password
            ):
                continue

            try:
                fiel = company._get_fiel_instance()
                info = fiel.validate()
                company.l10n_mx_sat_fiel_rfc = info['rfc']
                company.l10n_mx_sat_fiel_serial = info['serial']
                company.l10n_mx_sat_fiel_not_after = info['not_after']
                company.l10n_mx_sat_fiel_valid = info['valid']
            except Exception as e:
                _logger.warning(
                    "Error al validar FIEL de %s: %s",
                    company.name, e,
                )

    # =========================================================================
    # Métodos de negocio
    # =========================================================================
    def _get_fiel_instance(self) -> FIEL:
        """
        Construye y retorna una instancia de FIEL a partir de los campos
        almacenados en la compañía.

        Returns:
            Instancia de lib.sat_webservice.FIEL

        Raises:
            UserError: si falta alguno de los tres componentes.
        """
        self.ensure_one()
        if not self.l10n_mx_sat_fiel_cer:
            raise UserError(_(
                "No se ha cargado el certificado (.cer) de la FIEL "
                "para la empresa %(company)s.",
                company=self.name,
            ))
        if not self.l10n_mx_sat_fiel_key:
            raise UserError(_(
                "No se ha cargado la llave privada (.key) de la FIEL "
                "para la empresa %(company)s.",
                company=self.name,
            ))
        if not self.l10n_mx_sat_fiel_password:
            raise UserError(_(
                "No se ha configurado la contraseña de la FIEL "
                "para la empresa %(company)s.",
                company=self.name,
            ))

        cer_bytes = base64.b64decode(self.l10n_mx_sat_fiel_cer)
        key_bytes = base64.b64decode(self.l10n_mx_sat_fiel_key)

        try:
            return FIEL(
                cer_der=cer_bytes,
                key_der=key_bytes,
                password=self.l10n_mx_sat_fiel_password,
            )
        except ValueError as e:
            raise UserError(_(
                "Error al cargar la FIEL: %(error)s. "
                "Verifique que la contraseña sea correcta y que los archivos "
                ".cer y .key correspondan a una FIEL vigente.",
                error=str(e),
            )) from e

    def action_validate_fiel(self):
        """Acción de botón para validar la FIEL manualmente."""
        self.ensure_one()
        fiel = self._get_fiel_instance()
        info = fiel.validate()

        if not info['valid']:
            errors = '\n'.join(info['errors'])
            raise UserError(_(
                "La FIEL NO es válida:\n%(errors)s",
                errors=errors,
            ))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("FIEL Válida"),
                'message': _(
                    "RFC: %(rfc)s — Vigente hasta: %(expiry)s",
                    rfc=info['rfc'],
                    expiry=info['not_after'],
                ),
                'type': 'success',
                'sticky': False,
            },
        }
