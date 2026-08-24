# -*- coding: utf-8 -*-
"""Pre-migration 19.0.1.2.0 — Sanear columnas NULL antes del schema sync.

Corre ANTES de que Odoo aplique NOT NULL constraints durante el upgrade.
Cada bloque verifica primero que la columna exista (info_schema) para ser
compatible con instancias que no tengan algunos módulos instalados.

Campos cubiertos:
  - account_account.create_asset          → 'no'
  - website.shop_default_sort             → 'website_published desc, id desc'
  - website.product_page_image_layout     → 'carousel'
  - website.ecommerce_access              → 'everyone'
  - purchase_order.picking_type_id        → primer tipo 'incoming' de la empresa
  - product_template.base_unit_count      → 1.0
  - product_template.publish_date         → NOW() (solo si columna existe)
  - account_reports_export_wizard.folder_id → primera carpeta raíz (si tabla existe)
"""
import logging

_logger = logging.getLogger(__name__)


def _col_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    # ── account_account.create_asset ──────────────────────────────────────────
    if _col_exists(cr, 'account_account', 'create_asset'):
        cr.execute(
            "UPDATE account_account SET create_asset = 'no' WHERE create_asset IS NULL"
        )
        if cr.rowcount:
            _logger.info(
                "[ai_fields 19.0.1.2.0] account_account.create_asset NULL→'no' en %s filas",
                cr.rowcount,
            )

    # ── website: varios campos de e-commerce ──────────────────────────────────
    website_patches = [
        ('shop_default_sort',           'website_published desc, id desc'),
        ('product_page_image_layout',   'carousel'),
        ('ecommerce_access',            'everyone'),
    ]
    for col, default in website_patches:
        if _col_exists(cr, 'website', col):
            cr.execute(
                f"UPDATE website SET {col} = %s WHERE {col} IS NULL",
                (default,),
            )
            if cr.rowcount:
                _logger.info(
                    "[ai_fields 19.0.1.2.0] website.%s NULL→'%s' en %s filas",
                    col, default, cr.rowcount,
                )

    # ── purchase_order.picking_type_id ────────────────────────────────────────
    if _col_exists(cr, 'purchase_order', 'picking_type_id'):
        # Intento 1: picking type 'incoming' que pertenezca a la misma empresa.
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

        # Intento 2: fallback global para POs sin company_id o sin warehouse en empresa.
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
                "[ai_fields 19.0.1.2.0] purchase_order.picking_type_id NULL→tipo_incoming en %s filas",
                updated,
            )

    # ── product_template.base_unit_count ─────────────────────────────────────
    if _col_exists(cr, 'product_template', 'base_unit_count'):
        cr.execute(
            "UPDATE product_template SET base_unit_count = 1.0 WHERE base_unit_count IS NULL"
        )
        if cr.rowcount:
            _logger.info(
                "[ai_fields 19.0.1.2.0] product_template.base_unit_count NULL→1.0 en %s filas",
                cr.rowcount,
            )

    # ── product_template.publish_date ─────────────────────────────────────────
    if _col_exists(cr, 'product_template', 'publish_date'):
        cr.execute(
            "UPDATE product_template SET publish_date = NOW() WHERE publish_date IS NULL"
        )
        if cr.rowcount:
            _logger.info(
                "[ai_fields 19.0.1.2.0] product_template.publish_date NULL→NOW() en %s filas",
                cr.rowcount,
            )

    # ── account_reports_export_wizard.folder_id ───────────────────────────────
    # Es un TransientModel; rara vez tiene filas persistentes, pero se sana
    # preventivamente usando la primera carpeta raíz de documents si existe.
    if _col_exists(cr, 'account_reports_export_wizard', 'folder_id'):
        cr.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'documents_folder'
            """
        )
        if cr.fetchone():
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
                    "[ai_fields 19.0.1.2.0] account_reports_export_wizard.folder_id NULL→raíz en %s filas",
                    cr.rowcount,
                )
