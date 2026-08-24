# -*- coding: utf-8 -*-
from odoo import api, fields, models


class L10nMxSatAccountGroupCode(models.Model):
    """Código agrupador del SAT (Anexo 24 de la RMF vigente).

    Tabla de referencia, no editable por el usuario en el día a día: se
    carga completa desde data/l10n_mx_sat_account_group_code.csv,
    transcrita directamente del Anexo 24 (DOF, fuente oficial).
    """

    _name = "l10n_mx.sat.account.group.code"
    _description = "Código Agrupador de Cuentas SAT (Anexo 24)"
    _order = "code"

    code = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    level = fields.Selection(
        [
            ("0", "Rubro (no asignable a una cuenta)"),
            ("1", "Cuenta de nivel mayor"),
            ("2", "Subcuenta de primer nivel"),
            ("n", "Uso exclusivo sector financiero"),
        ],
        required=True,
    )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.code} - {rec.name}"
