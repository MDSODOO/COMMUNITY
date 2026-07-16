# -*- coding: utf-8 -*-
"""Migration 19.0.1.12.0 — Corrige el formato del complemento CFDI 4.0.

Problema: la versión 19.0.1.9.0 re-activó las vistas heredadas de
l10n_mx_edi sobre account.report_invoice_document. Combinado con el
template pharma_invoice_sat_footer que este módulo siempre ha tenido
activo, el resultado fue DOS bloques CFDI en el PDF: el nativo de
l10n_mx_edi y el custom.

Solución: desactivar las vistas l10n_mx_edi sobre el reporte de
facturas. El complemento CFDI custom (pharma_invoice_sat_footer)
pasa a ser el único bloque activo. El CSS también suprime el bloque
nativo como defensa adicional (via .inv-active [class*="l10n_mx_edi_cfdi"]).
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    from odoo.addons.custom_invoice_format import (
        _disable_native_mx_invoice_views,
        _synchronize_invoice_report_actions,
    )

    _logger.info(
        "custom_invoice_format 19.0.1.12.0: desactivando vistas nativas "
        "l10n_mx_edi para corregir complemento CFDI duplicado en PDF..."
    )
    _disable_native_mx_invoice_views(env)
    _synchronize_invoice_report_actions(env)
    _logger.info("custom_invoice_format 19.0.1.12.0: migración completada.")
