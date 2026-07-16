# -*- coding: utf-8 -*-
"""
Migration 19.0.0.6 — Erradica el warning "Duplicate labels" entre
`md_authorization_check_display` y `md_authorization_check_number`
en `account.move` y `account.bank.statement.line`.

Contexto:
  * En account.move, sale_account_custom define ambos campos en
    Python. Aunque cambiamos el `string` del display field, el cache
    de ir.model.fields puede quedar con la etiqueta vieja hasta que
    se reescribe explicitamente.
  * En account.bank.statement.line, los mismos nombres de campo
    fueron creados por Studio (origen "Modules: None" en el log).
    Hay que renombrar tambien ahi su field_description.

Esta migration fuerza el field_description correcto en ambos modelos.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

TARGET_MODELS = ('account.move', 'account.bank.statement.line')
LABEL_DISPLAY = 'Número de autorización o cheque (Vista)'
LABEL_NUMBER = 'Número de autorización o cheque'


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    display_fields = env['ir.model.fields'].sudo().search([
        ('name', '=', 'md_authorization_check_display'),
        ('model', 'in', TARGET_MODELS),
    ])
    to_update_display = display_fields.filtered(
        lambda f: f.field_description != LABEL_DISPLAY
    )
    if to_update_display:
        to_update_display.write({'field_description': LABEL_DISPLAY})
        _logger.info(
            "sale_account_custom 19.0.0.6: renombrados %d campos "
            "md_authorization_check_display a '%s' (modelos: %s)",
            len(to_update_display),
            LABEL_DISPLAY,
            ', '.join(to_update_display.mapped('model')),
        )

    number_fields = env['ir.model.fields'].sudo().search([
        ('name', '=', 'md_authorization_check_number'),
        ('model', 'in', TARGET_MODELS),
    ])
    to_update_number = number_fields.filtered(
        lambda f: f.field_description != LABEL_NUMBER
    )
    if to_update_number:
        to_update_number.write({'field_description': LABEL_NUMBER})
        _logger.info(
            "sale_account_custom 19.0.0.6: renombrados %d campos "
            "md_authorization_check_number a '%s' (modelos: %s)",
            len(to_update_number),
            LABEL_NUMBER,
            ', '.join(to_update_number.mapped('model')),
        )
