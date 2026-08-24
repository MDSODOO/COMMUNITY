# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    l10n_mx_sat_group_code_id = fields.Many2one(
        comodel_name="l10n_mx.sat.account.group.code",
        string="Código agrupador SAT",
        domain=[("level", "in", ("1", "2"))],
        help="Código agrupador del Anexo 24 del SAT que corresponde a esta "
        "cuenta, para el Catálogo de Cuentas de la Contabilidad "
        "Electrónica. Solo se permiten códigos de nivel 1 o 2 -- los "
        "rubros (nivel 0) no son asignables directamente.",
    )
