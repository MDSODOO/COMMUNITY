# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)

_TARGET_MODEL = "account.bank.statement.line"
_TARGET_METHOD = "_cron_try_auto_reconcile_statement_lines"
_SERVER_ACTION_CODE = (
    "model.with_context(mail_notify_force_send=False)"
    "._cron_try_auto_reconcile_statement_lines(batch_size=15)"
)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ServerAction = env["ir.actions.server"].sudo()

    actions = ServerAction.search([
        ("model_id.model", "=", _TARGET_MODEL),
        ("state", "=", "code"),
        ("code", "ilike", _TARGET_METHOD),
    ])

    if not actions:
        _logger.warning(
            "No se encontro accion de servidor sobre %s con llamada a %s; "
            "no se ajusto batch/contexto.",
            _TARGET_MODEL,
            _TARGET_METHOD,
        )
        return

    for action in actions:
        if action.code == _SERVER_ACTION_CODE:
            _logger.info(
                "La accion de servidor %s (%s) ya ejecuta %s con contexto "
                "seguro.",
                action.id,
                action.name,
                _TARGET_METHOD,
            )
            continue

        action.write({"code": _SERVER_ACTION_CODE})
        _logger.info(
            "Actualizada accion de servidor %s (%s): %s con batch_size=15 "
            "y mail_notify_force_send=False.",
            action.id,
            action.name,
            _TARGET_METHOD,
        )
