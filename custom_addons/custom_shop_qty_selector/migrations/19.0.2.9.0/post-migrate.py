"""Post-migration 19.0.2.9.0 — fix shop 404s + base_unit_count warning.

Contexto: el log de medicinedepot-main mostraba 404s en /shop/<slug>-<id>
para productos como 2458 ("mini-tratamiento-una-milagrosa-rosa-45ml-by-apple")
con error "Access Denied by record rules for operation: read ... uid: 4,
model: product.template". Diagnostico (ver discussion 2026-05-12):

  - uid 4 = Public User. La regla nativa de website filtra por
    is_published=True; cualquier producto sale_ok con barcode y precio
    que tenga is_published=False devuelve 404 al publico.
  - Nuestro catalogo tiene productos comerciales (barcode + list_price)
    despublicados por imports/migraciones previas.

Esta migracion:

  1. Republica product.template con TODAS estas condiciones:
        sale_ok = TRUE
        is_published = FALSE
        list_price > 0
        EXISTS variante con barcode no vacio
     (Criterio defensivo: NO toca productos sin barcode/precio,
      que probablemente son borradores o variantes internas.)

  2. Corrige product_product.base_unit_count NULL -> 0. El warning
     "Missing not-null constraint on product.product.base_unit_count"
     viene de migraciones desde versiones <17 donde el campo no era
     required. Setear 0 (el default declarativo) permite que Odoo
     reaplique el NOT NULL al sincronizar esquema.

Nota SQL: barcode es campo related en product.template
(related='product_variant_ids.barcode'); la columna fisica vive en
product_product. Por eso filtramos via EXISTS contra product_product.

Idempotente: re-correr no hace cambios adicionales (UPDATE con WHERE
ya hace no-op despues de la primera pasada).
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # ── 1. base_unit_count NULL -> 0 ────────────────────────────────
    cr.execute(
        """
        UPDATE product_product
        SET base_unit_count = 0
        WHERE base_unit_count IS NULL
        """
    )
    buc_fixed = cr.rowcount
    _logger.info(
        "[custom_shop_qty_selector 19.0.2.9.0] base_unit_count NULL->0 en %s product.product",
        buc_fixed,
    )

    # ── 2. Republica productos comerciales accidentalmente ocultos ──
    #    barcode vive en product_product (related en template),
    #    por eso filtramos via EXISTS contra la tabla de variantes.
    cr.execute(
        """
        UPDATE product_template pt
        SET is_published = TRUE
        WHERE pt.is_published = FALSE
          AND pt.sale_ok = TRUE
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
    republished = cr.rowcount
    _logger.info(
        "[custom_shop_qty_selector 19.0.2.9.0] republicados %s product.template (sale_ok+barcode+price)",
        republished,
    )

    # ── 3. Audit informativo: productos publicados restringidos a
    #       website_id especifico (no se modifican — multi-tenant safe) ─
    cr.execute(
        """
        SELECT COUNT(*) FROM product_template
        WHERE website_id IS NOT NULL
          AND is_published = TRUE
        """
    )
    website_scoped = cr.fetchone()[0]
    if website_scoped:
        _logger.info(
            "[custom_shop_qty_selector 19.0.2.9.0] %s productos publicados con website_id explicito (no modificados)",
            website_scoped,
        )

    # ── 4. Audit informativo: productos despublicados con sospecha
    #       de actividad comercial pero sin alguno de los criterios
    #       fuertes (sin barcode O sin precio). Solo log para revision
    #       manual; no se republican automaticamente. ────────────────
    cr.execute(
        """
        SELECT COUNT(*)
        FROM product_template pt
        WHERE pt.is_published = FALSE
          AND pt.sale_ok = TRUE
          AND (
              pt.list_price <= 0
              OR NOT EXISTS (
                  SELECT 1
                  FROM product_product pp
                  WHERE pp.product_tmpl_id = pt.id
                    AND pp.active = TRUE
                    AND pp.barcode IS NOT NULL
                    AND pp.barcode <> ''
              )
          )
        """
    )
    suspicious = cr.fetchone()[0]
    if suspicious:
        _logger.info(
            "[custom_shop_qty_selector 19.0.2.9.0] %s productos despublicados con sale_ok pero sin barcode/precio (NO modificados, revisar manualmente)",
            suspicious,
        )
