# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Distingue el carrito de la app móvil de cualquier otra cotización en
    # borrador (ej. las que crea un vendedor a mano) para el mismo partner --
    # sin esto, "el carrito activo" sería ambiguo.
    x_mobile_cart = fields.Boolean(
        string='Creado desde la app móvil', default=False, copy=False,
    )
