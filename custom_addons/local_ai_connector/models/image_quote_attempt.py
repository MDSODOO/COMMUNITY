# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models


class LocalAiImageQuoteAttempt(models.Model):
    _name = "local.ai.image.quote.attempt"
    _description = (
        "Registro de intentos POST a /ai/quote_from_image, para rate "
        "limiting real compartido entre workers -- mismo patron ya "
        "verificado en medicine.depot.affiliation.attempt (el contador en "
        "memoria de un solo proceso no sirve con workers > 1). El limite "
        "aqui es mas estricto que el de afiliacion porque cada solicitud "
        "cuesta 90-240s de CPU + hasta 6.7GB de RAM (modelo de vision), no "
        "solo un registro en Postgres."
    )
    _order = "create_date desc"

    ip_address = fields.Char(string="Dirección IP", required=True, index=True)

    @api.model
    def _gc_old_attempts(self, older_than_hours=24):
        threshold = fields.Datetime.now() - timedelta(hours=older_than_hours)
        self.search([('create_date', '<', threshold)]).unlink()
