# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_affiliation_status = fields.Selection(
        [('pending', 'Pendiente de aprobación'), ('approved', 'Aprobado')],
        string='Estado de Afiliación',
        tracking=True,
        help=(
            "Se establece en 'pending' automáticamente al crear un contacto nuevo "
            "desde el formulario público /afiliacion. Mientras esté pendiente, la "
            "cuenta no tiene acceso a la tienda (ver controllers/public.py, "
            "WebsiteSaleShopAccess.shop()). Vacío para contactos que no vinieron "
            "de ese formulario (no se les fuerza este flujo)."
        ),
    )

    def action_approve_affiliation(self):
        self.write({'x_affiliation_status': 'approved'})
