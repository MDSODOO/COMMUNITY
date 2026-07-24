# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)

_ACTION_ID = 1063
_ACTION_NAME = "Mapeo de Cuentas Contables"

_SERVER_ACTION_CODE = """ACCOUNT_MAPPING = {
    '401.01.01': '402.01.02',
    '401.04.01': '402.02.02',
    '401.40.01': '402.05.01',
}

# Extraer IDs puramente numericos para romper la referencia al cursor viejo
record_ids = records.ids
record_model = records._name

new_cr = env.registry.cursor()
try:
    new_env = env(cr=new_cr)

    account_objects = {}
    for from_code, to_code in ACCOUNT_MAPPING.items():
        from_acc = new_env['account.account'].search([('code', '=', from_code)], limit=1)
        if from_acc:
            account_objects[from_code] = from_acc

        to_acc = new_env['account.account'].search([('code', '=', to_code)], limit=1)
        if to_acc:
            account_objects[to_code] = to_acc

    safe_records = new_env[record_model].browse(record_ids)

    for invoice in safe_records:
        for line in invoice.invoice_line_ids:
            if line.account_id:
                current_code = line.account_id.code
                current_label = line.name or ""
                current_analytic = line.analytic_distribution or False

                if current_code in ACCOUNT_MAPPING and "Reembolso" in str(current_label):
                    if current_code in account_objects and ACCOUNT_MAPPING[current_code] in account_objects:
                        from_obj = account_objects[current_code]
                        to_obj = account_objects[ACCOUNT_MAPPING[current_code]]

                        if line.account_id.id == from_obj.id and line.account_id.id != to_obj.id:
                            line.write({
                                'account_id': to_obj.id,
                                'analytic_distribution': current_analytic
                            })
    new_cr.commit()
except Exception as e:
    new_cr.rollback()
    raise e
finally:
    new_cr.close()"""


def _find_target_action(env):
    ServerAction = env["ir.actions.server"].sudo()
    action_by_id = ServerAction.browse(_ACTION_ID).exists()
    if action_by_id and action_by_id.name == _ACTION_NAME:
        return action_by_id

    if action_by_id:
        _logger.warning(
            "La accion de servidor %s existe pero su nombre es %r; se intenta resolver por nombre.",
            _ACTION_ID,
            action_by_id.name,
        )

    action_by_name = ServerAction.search([("name", "=", _ACTION_NAME)], limit=1)
    if action_by_name:
        return action_by_name

    return ServerAction.browse()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = _find_target_action(env)
    if not action:
        _logger.warning(
            "No se encontro la accion de servidor %s (%s); no se aplico el fix de cursor aislado.",
            _ACTION_ID,
            _ACTION_NAME,
        )
        return

    if action.code == _SERVER_ACTION_CODE:
        _logger.info(
            "La accion de servidor %s (%s) ya tenia aplicado el fix de cursor aislado.",
            action.id,
            action.name,
        )
        return

    action.write({"code": _SERVER_ACTION_CODE})
    _logger.info(
        "Actualizada la accion de servidor %s (%s) con rebrowse por IDs y cursor independiente.",
        action.id,
        action.name,
    )
