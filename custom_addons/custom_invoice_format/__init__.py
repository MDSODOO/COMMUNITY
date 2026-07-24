# -*- coding: utf-8 -*-

import logging

from . import models

_logger = logging.getLogger(__name__)


def _disable_native_mx_invoice_views(env):
    """Desactiva las vistas QWeb de `l10n_mx_edi` heredadas sobre
    `account.report_invoice_document` para evitar que se rendericen
    DOS bloques CFDI en el PDF.

    Contexto: `pharma_invoice_sat_footer` es el bloque CFDI oficial de
    este módulo. Si las vistas nativas de l10n_mx_edi permanecen activas,
    se renderizan ambos bloques → el PDF muestra el complemento duplicado
    o mal formado.

    Esta función es el inverso de la lógica que introdujo v19.0.1.9.0
    (que re-activaba estas vistas). A partir de v19.0.1.12.0, el criterio
    es mantener SOLO el bloque custom y suprimir el nativo por CSS + esta
    desactivación de vista.
    """
    base_view = env.ref('account.report_invoice_document',
                        raise_if_not_found=False)
    if not base_view:
        _logger.warning(
            "custom_invoice_format: account.report_invoice_document "
            "no encontrada; no se desactivan vistas l10n_mx_edi."
        )
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

    to_disable = env['ir.ui.view'].sudo().with_context(
        active_test=False
    ).browse(list(candidate_ids)).filtered(
        lambda v: v.active
        and (v.key or '').startswith('l10n_mx_edi.')
        and v.id != base_view.id
    )
    if to_disable:
        to_disable.write({'active': False})
        _logger.info(
            "custom_invoice_format: desactivadas %d vistas l10n_mx_edi "
            "heredadas de account.report_invoice_document: %s",
            len(to_disable),
            ', '.join(to_disable.mapped('key')),
        )
    else:
        _logger.info(
            "custom_invoice_format: no había vistas l10n_mx_edi activas "
            "sobre account.report_invoice_document. Nada que desactivar."
        )


# Alias por retrocompatibilidad con scripts de migración que puedan
# referenciar el nombre anterior.
_restore_native_mx_invoice_views = _disable_native_mx_invoice_views


def _synchronize_invoice_report_actions(env):
    """Force invoice/bill report actions to use the same A4 paperformat.

    Odoo 19 keeps the invoice QWeb template ids separate from the report
    action ids. We only synchronize the real `ir.actions.report` records so
    the PDF stack stays consistent across customer invoices and supplier
    bills without colliding with `ir.ui.view` XMLIDs.
    """
    paperformat = env.ref(
        'custom_invoice_format.paperformat_invoice_pharma',
        raise_if_not_found=False,
    )
    if not paperformat:
        _logger.warning(
            "custom_invoice_format: paperformat_invoice_pharma not found; "
            "invoice report actions were not synchronized."
        )
        return

    report_xmlids = (
        'account.account_invoices',
        'account.account_invoices_without_payment',
        'account.action_account_original_vendor_bill',
    )
    for xmlid in report_xmlids:
        report = env.ref(xmlid, raise_if_not_found=False)
        if report and 'paperformat_id' in report._fields and report.paperformat_id != paperformat:
            report.sudo().write({'paperformat_id': paperformat.id})


def post_init_hook(env):
    _disable_native_mx_invoice_views(env)
    _synchronize_invoice_report_actions(env)



def post_load():
    """Hook por proceso (sin env). No tocamos BD aqui."""
    return
