"""Pre-migration 19.0.2.12.0 — sanear product_product.base_unit_count.

Corre ANTES de la sincronizacion de schema. Asi cuando Odoo aplica la
not-null constraint en product_product.base_unit_count ya no encuentra
NULLs y la constraint se aplica con exito. El warning recurrente
"odoo.schema: Missing not-null constraint on product.product.base_unit_count"
desaparece a partir de este upgrade y no vuelve a emitirse en arranques
posteriores.

Versiones previas (19.0.2.9.0 / 19.0.2.10.0 / 19.0.2.11.0) ya hacian este
UPDATE pero en post-migrate, demasiado tarde: Odoo emite el warning ANTES
de correr post-migrate, por eso persistia en cada reinicio.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'product_product'
          AND column_name = 'base_unit_count'
        """
    )
    if not cr.fetchone():
        return

    cr.execute(
        """
        UPDATE product_product
        SET base_unit_count = 0
        WHERE base_unit_count IS NULL
        """
    )
    if cr.rowcount:
        _logger.info(
            "[custom_shop_qty_selector 19.0.2.12.0 pre-migrate] "
            "base_unit_count NULL->0 en %s product.product",
            cr.rowcount,
        )
