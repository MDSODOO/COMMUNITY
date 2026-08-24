# -*- coding: utf-8 -*-
"""NullSanitizer — limpia NULLs en columnas requeridas de módulos externos.

Este modelo existe ÚNICAMENTE para que su _auto_init() corra en cada
arranque de Odoo (no solo durante upgrades). Esto garantiza que las
columnas con NOT NULL requerido no tengan NULLs antes de que el ORM
de account, website y purchase evalúe sus constraints.

Flujo:
  arranque → NullSanitizer._auto_init() → limpia NULLs vía SQL raw
           → super()._auto_init() (crea tabla vacía de este modelo)
           → ...account.account._auto_init() corre después, sin NULLs
             → Odoo aplica ALTER TABLE SET NOT NULL → warning eliminado.

Tras el primer arranque limpio el constraint queda en la BD y los
arranques posteriores no emiten ningún warning (la columna ya tiene
NOT NULL a nivel PostgreSQL).
"""
import logging
from odoo import models

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

    remaining = _null_count(cr, 'website', column)
    if remaining:
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
        filled = cr.rowcount
        if filled:
            _logger.info(
                "[ai_fields] website.%s NULL saneados: copiados=%s, default='%s'=%s",
                column, copied, default_label, filled,
            )
    elif copied:
        _logger.info(
            "[ai_fields] website.%s NULL saneados por copia de valor existente: %s",
            column, copied,
        )


def _sanitize_nulls(cr):
    """Limpia NULLs en columnas requeridas de módulos externos.
    Idempotente: UPDATE WHERE IS NULL afecta 0 filas si ya no hay NULLs.
    """
    # ── account_account.create_asset ─────────────────────────────────────────
    if _col_exists(cr, 'account_account', 'create_asset'):
        cr.execute(
            "UPDATE account_account SET create_asset = 'no' WHERE create_asset IS NULL"
        )
        if cr.rowcount:
            _logger.info(
                "[ai_fields] account_account.create_asset NULL→'no': %s filas", cr.rowcount
            )

    # ── website: campos de e-commerce ────────────────────────────────────────
    _WEBSITE_PATCHES = [
        ('shop_default_sort', 'website_published desc, id desc'),
        ('product_page_image_layout', 'carousel'),
        ('product_page_image_width', '50'),
        ('product_page_image_spacing', '0'),
        ('product_page_image_roundness', '0'),
        ('product_page_image_ratio', '1x1'),
        ('product_page_image_ratio_mobile', '1x1'),
        ('ecommerce_access', 'everyone'),
    ]
    for col, default in _WEBSITE_PATCHES:
        _sanitize_website_column(cr, col, default)

    # ── purchase_order.picking_type_id ────────────────────────────────────────
    if _col_exists(cr, 'purchase_order', 'picking_type_id') and _table_exists(
        cr, 'stock_picking_type'
    ):
        cr.execute(
            """
            UPDATE purchase_order po
               SET picking_type_id = (
                   SELECT spt.id
                     FROM stock_picking_type spt
                     JOIN stock_warehouse sw ON sw.id = spt.warehouse_id
                    WHERE spt.code = 'incoming'
                      AND sw.company_id = po.company_id
                    ORDER BY spt.id ASC
                    LIMIT 1
               )
             WHERE po.picking_type_id IS NULL
               AND po.company_id IS NOT NULL
            """
        )
        updated = cr.rowcount
        cr.execute(
            """
            UPDATE purchase_order po
               SET picking_type_id = (
                   SELECT id FROM stock_picking_type
                    WHERE code = 'incoming'
                    ORDER BY id ASC LIMIT 1
               )
             WHERE po.picking_type_id IS NULL
            """
        )
        updated += cr.rowcount
        if updated:
            _logger.info(
                "[ai_fields] purchase_order.picking_type_id NULL→incoming: %s filas", updated
            )

    # ── product_template.base_unit_count ─────────────────────────────────────
    if _col_exists(cr, 'product_template', 'base_unit_count'):
        cr.execute(
            "UPDATE product_template SET base_unit_count = 1.0 WHERE base_unit_count IS NULL"
        )
        if cr.rowcount:
            _logger.info(
                "[ai_fields] product_template.base_unit_count NULL→1.0: %s filas", cr.rowcount
            )

    # ── product_product.base_unit_count ──────────────────────────────────────
    if _col_exists(cr, 'product_product', 'base_unit_count'):
        cr.execute(
            "UPDATE product_product SET base_unit_count = 0 WHERE base_unit_count IS NULL"
        )
        if cr.rowcount:
            _logger.info(
                "[ai_fields] product_product.base_unit_count NULL→0: %s filas", cr.rowcount
            )

    # ── account_reports_export_wizard.folder_id ───────────────────────────────
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
                "[ai_fields] account_reports_export_wizard.folder_id NULL→raíz: %s filas",
                updated,
            )


class AiFieldsNullSanitizer(models.Model):
    """Modelo técnico vacío cuyo único propósito es ejecutar _sanitize_nulls
    en cada arranque de Odoo, antes de que el ORM valide NOT NULL constraints
    de los modelos externos (account, website, purchase, product).
    """

    _name = 'ai.fields.null.sanitizer'
    _description = 'NULL Sanitizer (Technical)'

    def _auto_init(self):
        _sanitize_nulls(self.env.cr)
        super()._auto_init()
