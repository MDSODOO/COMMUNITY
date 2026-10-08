# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class MedicineDepotAffiliationAttempt(models.Model):
    _name = "medicine.depot.affiliation.attempt"
    _description = (
        "Registro de intentos POST a /afiliacion. Existe para dar rate "
        "limiting real y compartido entre los workers de Odoo (el "
        "contador en memoria de un solo proceso no sirve con workers > 1)."
    )
    _order = "create_date desc"

    ip_address = fields.Char(string="Dirección IP", required=True, index=True)

    @api.model
    def _gc_old_attempts(self, older_than_hours=24):
        """Purga intentos viejos para que la tabla no crezca indefinidamente."""
        threshold = fields.Datetime.now() - timedelta(hours=older_than_hours)
        self.search([('create_date', '<', threshold)]).unlink()
