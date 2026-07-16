"""Post-migration 19.0.2.11.0 - defensive retry for production upgrades.

This version intentionally repeats the safe data repairs from previous
migrations, but every SQL block first checks that the target columns exist.
That keeps Odoo.sh builds from failing on databases whose schema is between
module states during a test-to-main upgrade.
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
            "[custom_shop_qty_selector 19.0.2.11.0] se omite bloque SQL: faltan columnas %s.%s",
            table,
            sorted(missing),
        )
    return not missing


def _repair_base_unit_count(cr):
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
        "[custom_shop_qty_selector 19.0.2.11.0] base_unit_count NULL->0 en %s product.product",
        cr.rowcount,
    )


def _republish_global_shop_products(cr):
    if not _has_columns(
        cr,
        'product_template',
        {'id', 'is_published', 'sale_ok', 'website_id', 'list_price'},
    ):
        return
    if not _has_columns(
        cr,
        'product_product',
        {'product_tmpl_id', 'active', 'barcode'},
    ):
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
        "[custom_shop_qty_selector 19.0.2.11.0] republicados %s product.template globales",
        cr.rowcount,
    )


def _sync_studio_acls(cr):
    try:
        from odoo import SUPERUSER_ID, api
        from odoo.addons.custom_shop_qty_selector.hooks import _post_init_create_studio_acls
    except Exception:
        _logger.exception(
            "[custom_shop_qty_selector 19.0.2.11.0] no se pudo importar el hook de ACLs Studio"
        )
        return False

    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        _post_init_create_studio_acls(env)
    except Exception:
        _logger.exception(
            "[custom_shop_qty_selector 19.0.2.11.0] no se pudieron sincronizar las ACLs Studio"
        )
        return False
    return True


def migrate(cr, version):
    _repair_base_unit_count(cr)
    _republish_global_shop_products(cr)
    if _sync_studio_acls(cr):
        _logger.info("[custom_shop_qty_selector 19.0.2.11.0] ACLs Studio sincronizadas")
    else:
        _logger.warning("[custom_shop_qty_selector 19.0.2.11.0] ACLs Studio omitidas")
