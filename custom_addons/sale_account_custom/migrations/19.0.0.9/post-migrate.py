# -*- coding: utf-8 -*-
"""Clean up the orphan manual model x_sale.order.line.

The model was created manually and is not exposed by any installed module.
When it is empty and has no critical references, remove the metadata and
table. If rows or dependencies are found, create a conservative ACL instead
so Odoo no longer warns during registry loading.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

MODEL = 'x_sale.order.line'
TABLE = 'x_sale_order_line'
ACCESS_NAME = 'access_x_sale_order_line'


def _table_exists(cr, table):
    cr.execute("SELECT to_regclass(%s)", (table,))
    row = cr.fetchone()
    return bool(row and row[0])


def _table_count(cr, table):
    if not _table_exists(cr, table):
        return 0
    cr.execute('SELECT COUNT(*) FROM "%s"' % table)
    row = cr.fetchone()
    return int(row[0] or 0) if row else 0


def _count_model_dependencies(env, model):
    action_ids = env['ir.actions.act_window'].sudo().search([
        ('res_model', '=', model),
    ]).ids
    action_refs = ['ir.actions.act_window,%s' % action_id for action_id in action_ids]

    dependencies = {
        'referencing_fields': env['ir.model.fields'].sudo().search_count([
            ('relation', '=', model),
        ]),
        'views_by_model': env['ir.ui.view'].sudo().search_count([
            ('model', '=', model),
        ]),
        'views_by_arch': env['ir.ui.view'].sudo().search_count([
            ('arch_db', 'ilike', model),
        ]),
        'actions': len(action_ids),
        'rules': env['ir.rule'].sudo().search_count([
            ('model_id.model', '=', model),
        ]),
        'menus': env['ir.ui.menu'].sudo().search_count([
            ('action', 'in', action_refs),
        ]) if action_refs else 0,
    }
    return dependencies


def _has_critical_dependencies(dependencies):
    return any(count for count in dependencies.values())


def _ensure_access(env, ir_model):
    group_user = env.ref('base.group_user', raise_if_not_found=False)
    existing = env['ir.model.access'].sudo().search([
        ('model_id', '=', ir_model.id),
        ('group_id', '=', group_user.id if group_user else False),
    ], limit=1)
    values = {
        'name': ACCESS_NAME,
        'model_id': ir_model.id,
        'group_id': group_user.id if group_user else False,
        'perm_read': True,
        'perm_write': True,
        'perm_create': True,
        'perm_unlink': True,
    }
    if existing:
        existing.write(values)
        _logger.info(
            "sale_account_custom 19.0.0.9: ACL actualizada para %s", MODEL
        )
    else:
        env['ir.model.access'].sudo().create(values)
        _logger.info(
            "sale_account_custom 19.0.0.9: ACL creada para %s", MODEL
        )


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ir_model = env['ir.model'].sudo().search([('model', '=', MODEL)], limit=1)
    if not ir_model:
        _logger.info(
            "sale_account_custom 19.0.0.9: modelo %s no encontrado", MODEL
        )
        return

    row_count = _table_count(cr, TABLE)
    dependencies = _count_model_dependencies(env, MODEL)
    if row_count == 0 and not _has_critical_dependencies(dependencies):
        ir_model.unlink()
        cr.execute('DROP TABLE IF EXISTS "%s" CASCADE' % TABLE)
        _logger.info(
            "sale_account_custom 19.0.0.9: modelo manual %s eliminado; "
            "filas=%d dependencias=%s",
            MODEL,
            row_count,
            dependencies,
        )
        return

    _ensure_access(env, ir_model)
    _logger.warning(
        "sale_account_custom 19.0.0.9: modelo manual %s conservado; "
        "filas=%d dependencias=%s",
        MODEL,
        row_count,
        dependencies,
    )
