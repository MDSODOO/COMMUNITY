# -*- coding: utf-8 -*-
"""Migration 19.0.1.10.0.

Normaliza los report actions de factura para que el layout de cliente y
proveedor use el mismo template y el mismo paperformat A4. Odoo 19 separa
"Original Bills" como acción independiente; si queda con su template/paperformat
nativo, la factura de proveedor sale distinta a la de cliente.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    from odoo.addons.custom_invoice_format import (
        _synchronize_invoice_report_actions,
    )

    env = api.Environment(cr, SUPERUSER_ID, {})
    _synchronize_invoice_report_actions(env)
