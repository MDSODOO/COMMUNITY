# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    qfm_receipt_price_update_policy = fields.Selection(
        related='company_id.qfm_receipt_price_update_policy',
        readonly=False,
        string='Política de precio por recepción',
    )
