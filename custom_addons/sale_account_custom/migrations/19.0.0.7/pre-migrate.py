# -*- coding: utf-8 -*-
"""
Migration 19.0.0.7 — Crea las columnas almacenadas que el ORM no pudo generar
porque el módulo no fue actualizado cuando se declararon los campos.

Campos afectados en account_move:
  - preferid_payment_method_line (integer FK → l10n_mx_edi_payment_method)
  - md_authorization_check_number (varchar)

Se ejecuta como pre-migrate para que las columnas existan antes de que el ORM
las consulte durante el upgrade, evitando el UndefinedColumn.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # preferid_payment_method_line: Many2one → integer en PostgreSQL
    cr.execute("""
        ALTER TABLE account_move
        ADD COLUMN IF NOT EXISTS preferid_payment_method_line integer
    """)
    _logger.info(
        "sale_account_custom 19.0.0.7: columna preferid_payment_method_line "
        "asegurada en account_move"
    )

    # Poblar desde l10n_mx_edi_payment_method_id donde aún no tenga valor
    cr.execute("""
        UPDATE account_move
           SET preferid_payment_method_line = l10n_mx_edi_payment_method_id
         WHERE preferid_payment_method_line IS NULL
           AND l10n_mx_edi_payment_method_id IS NOT NULL
    """)
    cr.execute("SELECT COUNT(*) FROM account_move WHERE preferid_payment_method_line IS NOT NULL")
    count = cr.fetchone()[0]
    _logger.info(
        "sale_account_custom 19.0.0.7: %d registros populados en "
        "preferid_payment_method_line",
        count,
    )

    # md_authorization_check_number: Char → varchar en PostgreSQL
    cr.execute("""
        ALTER TABLE account_move
        ADD COLUMN IF NOT EXISTS md_authorization_check_number varchar
    """)
    _logger.info(
        "sale_account_custom 19.0.0.7: columna md_authorization_check_number "
        "asegurada en account_move"
    )
