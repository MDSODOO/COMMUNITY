"""Post-migration 19.0.2.10.0 - conservative shop publication sync.

This migration keeps the 19.0.2.9.0 data repair idempotent while fixing its
main risk: never auto-publish products scoped to a specific website.
"""

import logging

_logger = logging.getLogger(__name__)


def _table_exists(cr, table):
    cr.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = %s
        """,
        [table],
    )
    return bool(cr.fetchone())


def _has_columns(cr, table, columns):
    if not _table_exists(cr, table):
        return False
    cr.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = ANY(%s)
        """,
        [table, list(columns)],
    )
    existing = {row[0] for row in cr.fetchall()}
    missing = set(columns) - existing
    if missing:
        _logger.warning(
            "[custom_shop_qty_selector migration] se omite bloque SQL: faltan columnas %s.%s",
            table,
            sorted(missing),
        )
    return not missing


def _repair_base_unit_count(cr, version_label):
    if not _has_columns(cr, 'product_product', {'base_unit_count'}):
        return
    cr.execute(
        """
        UPDATE product_product
        SET base_unit_count = 0
        WHERE base_unit_count IS NULL
        """
    )
    _logger.info(
        "[custom_shop_qty_selector %s] base_unit_count NULL->0 en %s product.product",
        version_label,
        cr.rowcount,
    )


def _republish_global_shop_products(cr, version_label):
    required_template_columns = {
        'id',
        'is_published',
        'sale_ok',
        'website_id',
        'list_price',
    }
    required_product_columns = {
        'product_tmpl_id',
        'active',
        'barcode',
    }
    if not _has_columns(cr, 'product_template', required_template_columns):
        return
    if not _has_columns(cr, 'product_product', required_product_columns):
        return

    cr.execute(
        """
        UPDATE product_template pt
        SET is_published = TRUE
        WHERE pt.is_published = FALSE
          AND pt.sale_ok = TRUE
          AND pt.website_id IS NULL
          AND pt.list_price > 0
          AND EXISTS (
              SELECT 1
              FROM product_product pp
              WHERE pp.product_tmpl_id = pt.id
                AND pp.active = TRUE
                AND pp.barcode IS NOT NULL
                AND pp.barcode <> ''
          )
        """
    )
    _logger.info(
        "[custom_shop_qty_selector %s] republicados %s product.template globales (sale_ok+barcode+price)",
        version_label,
        cr.rowcount,
    )


def _audit_website_scoped_products(cr, version_label):
    if not _has_columns(
        cr,
        'product_template',
        {'website_id', 'sale_ok', 'is_published'},
    ):
        return
    cr.execute(
        """
        SELECT COUNT(*)
        FROM product_template pt
        WHERE pt.website_id IS NOT NULL
          AND pt.sale_ok = TRUE
          AND pt.is_published = TRUE
        """
    )
    website_scoped = cr.fetchone()[0]
    if website_scoped:
        _logger.info(
            "[custom_shop_qty_selector %s] %s productos publicados con website_id explicito (audit only)",
            version_label,
            website_scoped,
        )


def _sync_studio_acls(cr):
    """Best-effort ACL sync for optional Studio models.

    Missing or inconsistent Studio metadata should not block the product data
    repair that this migration is meant to perform.
    """
    try:
        from odoo import SUPERUSER_ID, api
        from odoo.addons.custom_shop_qty_selector.hooks import _post_init_create_studio_acls
    except Exception:
        _logger.exception(
            "[custom_shop_qty_selector 19.0.2.10.0] no se pudo importar el hook de ACLs Studio"
        )
        return False

    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        _post_init_create_studio_acls(env)
    except Exception:
        _logger.exception(
            "[custom_shop_qty_selector 19.0.2.10.0] no se pudieron sincronizar las ACLs Studio"
        )
        return False
    return True


def migrate(cr, version):
    version_label = "19.0.2.10.0"
    _repair_base_unit_count(cr, version_label)
    _republish_global_shop_products(cr, version_label)
    _audit_website_scoped_products(cr, version_label)

    if _sync_studio_acls(cr):
        _logger.info("[custom_shop_qty_selector 19.0.2.10.0] ACLs Studio sincronizadas")
    else:
        _logger.warning("[custom_shop_qty_selector 19.0.2.10.0] ACLs Studio omitidas")
