# -*- coding: utf-8 -*-
"""Pre-migration 19.0.1.6.0 — Limpieza final de NULLs para NOT NULL base.

Objetivo:
  - Silenciar warnings `odoo.schema: Missing not-null constraint`
    en campos nativos de account/website/account_reports.
  - Mantener la operación idempotente y segura para múltiples corridas.
"""
import logging

_logger = logging.getLogger(__name__)


def _col_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())


def _table_exists(cr, table):
    cr.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (table,),
    )
    return bool(cr.fetchone())


def _col_data_type(cr, table, column):
    cr.execute(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    row = cr.fetchone()
    return row[0] if row else ''


def _null_count(cr, table, column):
    cr.execute(
        "SELECT COUNT(*) FROM " + table + " WHERE " + column + " IS NULL"
    )
    row = cr.fetchone()
    return int(row[0] or 0) if row else 0


def _sanitize_website_column(cr, column, text_default):
    if not _col_exists(cr, 'website', column):
        return

    # Paso 1: copiar valor válido existente para respetar configuración actual.
    cr.execute(
        "UPDATE website w "
        "SET " + column + " = src.value "
        "FROM ("
        "    SELECT " + column + " AS value "
        "    FROM website "
        "    WHERE " + column + " IS NOT NULL "
        "    ORDER BY id ASC LIMIT 1"
        ") src "
        "WHERE w." + column + " IS NULL"
    )
    copied = cr.rowcount

    # Paso 2: si aún quedan NULLs, aplicar fallback tipado.
    remaining = _null_count(cr, 'website', column)
    if not remaining:
        if copied:
            _logger.info(
                "[ai_fields 19.0.1.6.0] website.%s: NULL saneados por copia=%s",
                column, copied,
            )
        return

    data_type = _col_data_type(cr, 'website', column)
    if data_type in (
        'smallint',
        'integer',
        'bigint',
        'decimal',
        'numeric',
        'real',
        'double precision',
    ):
        cr.execute(
            "UPDATE website SET " + column + " = 0 WHERE " + column + " IS NULL"
        )
        default_label = '0'
    elif data_type == 'boolean':
        cr.execute(
            "UPDATE website SET " + column + " = FALSE WHERE " + column + " IS NULL"
        )
        default_label = 'False'
    else:
        cr.execute(
            "UPDATE website SET " + column + " = %s WHERE " + column + " IS NULL",
            (text_default,),
        )
        default_label = text_default

    if cr.rowcount:
        _logger.info(
            "[ai_fields 19.0.1.6.0] website.%s: NULL saneados copia=%s default('%s')=%s",
            column,
            copied,
            default_label,
            cr.rowcount,
        )


def migrate(cr, version):
    # ── account_account.create_asset ─────────────────────────────────────────
    if _col_exists(cr, 'account_account', 'create_asset'):
        cr.execute(
            "UPDATE account_account SET create_asset = 'no' WHERE create_asset IS NULL"
        )
        if cr.rowcount:
            _logger.info(
                "[ai_fields 19.0.1.6.0] account_account.create_asset NULL→'no': %s filas",
                cr.rowcount,
            )

    # ── website.* (campos de e-commerce y visuales de producto) ─────────────
    website_defaults = [
        ('shop_default_sort', 'website_published desc, id desc'),
        ('product_page_image_layout', 'carousel'),
        ('product_page_image_width', '50'),
        ('product_page_image_spacing', '0'),
        ('product_page_image_roundness', '0'),
        ('product_page_image_ratio', '1x1'),
        ('product_page_image_ratio_mobile', '1x1'),
        ('ecommerce_access', 'everyone'),
    ]
    for column, default in website_defaults:
        _sanitize_website_column(cr, column, default)

    # ── account_reports_export_wizard.folder_id ──────────────────────────────
    if _col_exists(cr, 'account_reports_export_wizard', 'folder_id') and _table_exists(
        cr, 'documents_folder'
    ):
        cr.execute(
            """
            UPDATE account_reports_export_wizard
               SET folder_id = (
                   SELECT id FROM documents_folder
                    WHERE parent_folder_id IS NULL
                    ORDER BY id ASC LIMIT 1
               )
             WHERE folder_id IS NULL
            """
        )
        updated = cr.rowcount
        cr.execute(
            """
            UPDATE account_reports_export_wizard
               SET folder_id = (
                   SELECT id FROM documents_folder
                    ORDER BY id ASC LIMIT 1
               )
             WHERE folder_id IS NULL
            """
        )
        updated += cr.rowcount
        if updated:
            _logger.info(
                "[ai_fields 19.0.1.6.0] account_reports_export_wizard.folder_id saneado: %s",
                updated,
            )
