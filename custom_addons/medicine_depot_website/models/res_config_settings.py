# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = 'Settings (MD website API keys)'

    google_maps_api_key = fields.Char(
        string='Google Maps API Key',
        config_parameter='medicine_depot.google_maps_key',
    )
