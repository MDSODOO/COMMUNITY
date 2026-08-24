# -*- coding: utf-8 -*-
"""Pre-migration 19.0.1.4.0 — Limpieza comprehensiva de NULLs.

Corre ANTES del schema sync durante el upgrade (-u ai_fields).
Consolida todas las correcciones de versiones anteriores (1.2.0, 1.3.0)
en un script único e idempotente, cubriendo el caso donde alguna
instancia haya saltado versiones intermedias.

A partir de esta versión, el modelo ai.fields.null.sanitizer cubre
los arranques sin upgrade mediante su _auto_init().
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


def migrate(cr, version):
    # ── account_account.create_asset ─────────────────────────────────────────
    if _col_exists(cr, 'account_account', 'create_asset'):
        cr.execute(
            "UPDATE account_account SET create_asset = 'no' WHERE create_asset IS NULL"
        )
        if cr.rowcount:
            _logger.info(
                "[ai_fields 19.0.1.4.0] account_account.create_asset NULL→'no': %s filas",
                cr.rowcount,
            )

    # ── website: campos de e-commerce ────────────────────────────────────────
    _WEBSITE_PATCHES = [
        ('shop_default_sort',         'website_published desc, id desc'),
        ('product_page_image_layout', 'carousel'),
        ('ecommerce_access',          'everyone'),
    ]
    for col, val in _WEBSITE_PATCHES:
        if _col_exists(cr, 'website', col):
            cr.execute(
                "UPDATE website SET " + col + " = %s WHERE " + col + " IS NULL",
                (val,),
            )
            if cr.rowcount:
                _logger.info(
                    "[ai_fields 19.0.1.4.0] website.%s NULL→'%s': %s filas",
                    col, val, cr.rowcount,
                )

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
                "[ai_fields 19.0.1.4.0] purchase_order.picking_type_id NULL→incoming: %s filas",
                updated,
            )

    # ── product_template / product_product: base_unit_count ──────────────────
    for table, default in [('product_template', '1.0'), ('product_product', '0')]:
        if _col_exists(cr, table, 'base_unit_count'):
            cr.execute(
                f"UPDATE {table} SET base_unit_count = {default} WHERE base_unit_count IS NULL"
            )
            if cr.rowcount:
                _logger.info(
                    "[ai_fields 19.0.1.4.0] %s.base_unit_count NULL→%s: %s filas",
                    table, default, cr.rowcount,
                )

    # ── product_template.publish_date ─────────────────────────────────────────
    if _col_exists(cr, 'product_template', 'publish_date'):
        cr.execute(
            "UPDATE product_template SET publish_date = NOW() WHERE publish_date IS NULL"
        )
        if cr.rowcount:
            _logger.info(
                "[ai_fields 19.0.1.4.0] product_template.publish_date NULL→NOW(): %s filas",
                cr.rowcount,
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
        if cr.rowcount:
            _logger.info(
                "[ai_fields 19.0.1.4.0] account_reports_export_wizard.folder_id: %s filas",
                cr.rowcount,
            )

    # ── res_users: logins duplicados ──────────────────────────────────────────
    cr.execute(
        """
        UPDATE res_users
           SET login = login || '_dup_' || id::text
         WHERE id IN (
             SELECT id FROM (
                 SELECT id,
                        ROW_NUMBER() OVER (
                            PARTITION BY login
                            ORDER BY active DESC, id ASC
                        ) AS row_num
                   FROM res_users
             ) t
              WHERE t.row_num > 1
         )
        """
    )
    if cr.rowcount:
        _logger.warning(
            "[ai_fields 19.0.1.4.0] %d login(s) duplicado(s) renombrado(s) "
            "con sufijo _dup_<id>. Revisar: login LIKE '%%_dup_%%'.",
            cr.rowcount,
        )

    # ── ir_model_fields: labels Studio ───────────────────────────────────────
    cr.execute(
        """
        UPDATE ir_model_fields
           SET field_description = 'Sucursal (Oficina)'
         WHERE name = 'x_studio_branch_office'
           AND field_description != 'Sucursal (Oficina)'
        """
    )
    if cr.rowcount:
        _logger.info(
            "[ai_fields 19.0.1.4.0] ir_model_fields → 'Sucursal (Oficina)': %s fila(s).",
            cr.rowcount,
        )
