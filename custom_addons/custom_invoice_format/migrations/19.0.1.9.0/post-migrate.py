# -*- coding: utf-8 -*-
"""
Migration 19.0.1.9.0 — Re-activa vistas l10n_mx_edi heredadas
sobre `account.report_invoice_document` que la version 19.0.1.8.0
habia desactivado.

Razon: el usuario opto por restaurar el bloque CFDI nativo
(UUID, sellos, cadena, QR generados por Odoo) y conservar
unicamente nuestra tabla de totales custom + columnas SAT visibles.

Esta migration replica el `post_init_hook` para que la re-activacion
se aplique en instancias donde el modulo ya estaba instalado.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    base_view = env.ref('account.report_invoice_document',
                        raise_if_not_found=False)
    if not base_view:
        return

    candidate_ids = {base_view.id}
    pending = [base_view.id]
    seen = set()
    while pending:
        next_round = []
        for vid in pending:
            if vid in seen:
                continue
            seen.add(vid)
            children = env['ir.ui.view'].sudo().with_context(
                active_test=False
            ).search([
                ('inherit_id', '=', vid),
                ('type', '=', 'qweb'),
            ])
            for c in children:
                candidate_ids.add(c.id)
                next_round.append(c.id)
        pending = next_round

    to_enable = env['ir.ui.view'].sudo().with_context(
        active_test=False
    ).browse(list(candidate_ids)).filtered(
        lambda v: not v.active
        and (v.key or '').startswith('l10n_mx_edi.')
        and v.id != base_view.id
    )
    if to_enable:
        to_enable.write({'active': True})
        _logger.info(
            "custom_invoice_format 19.0.1.9.0: re-activadas %d vistas "
            "l10n_mx_edi sobre account.report_invoice_document: %s",
            len(to_enable),
            ', '.join(to_enable.mapped('key')),
        )
