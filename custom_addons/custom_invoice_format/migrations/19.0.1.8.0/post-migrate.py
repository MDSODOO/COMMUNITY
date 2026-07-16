# -*- coding: utf-8 -*-
"""
Migration 19.0.1.8.0 — Desactiva vistas l10n_mx_edi heredadas
sobre `account.report_invoice_document`.

Razon: el complemento CFDI nativo de l10n_mx_edi se renderiza ademas
del bloque CFDI 4.0 que `custom_invoice_format` imprime. La duplicacion
fragmenta la factura a 3 paginas e imprime sellos como texto crudo
en la pagina 1.

Esta migration replica el `post_init_hook` para que la desactivacion
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
            children = env['ir.ui.view'].sudo().search([
                ('inherit_id', '=', vid),
                ('type', '=', 'qweb'),
            ])
            for c in children:
                candidate_ids.add(c.id)
                next_round.append(c.id)
        pending = next_round

    to_disable = env['ir.ui.view'].sudo().browse(list(candidate_ids)).filtered(
        lambda v: v.active
        and (v.key or '').startswith('l10n_mx_edi.')
        and v.id != base_view.id
    )
    if to_disable:
        to_disable.write({'active': False})
        _logger.info(
            "custom_invoice_format 19.0.1.8.0: desactivadas %d vistas "
            "l10n_mx_edi sobre account.report_invoice_document: %s",
            len(to_disable),
            ', '.join(to_disable.mapped('key')),
        )
