# -*- coding: utf-8 -*-
"""Migration 19.0.1.19.0 — Purga PDFs cacheados de facturas/notas de crédito
de proveedor (in_invoice / in_refund).

Problema: la migración 19.0.1.1.0 purgó los PDF cacheados en
account_move.invoice_pdf_report_file solo para move_type in
('out_invoice', 'out_refund') (documentos de cliente). Los documentos de
proveedor (in_invoice / in_refund) nunca se incluyeron, así que cualquier
Factura o Nota de Crédito de proveedor impresa/descargada antes del rediseño
pharma del header sigue sirviendo el PDF viejo cacheado — el reporte ya
genera el layout correcto para documentos nuevos, pero los ya cacheados no
se regeneran solos.

Repite la purga de 19.0.1.1.0 pero cubriendo los 4 move_type de factura
(in_invoice, in_refund, out_invoice, out_refund) para dejar todo el
histórico consistente con el template actual.
"""

def migrate(cr, version):
    cr.execute(
        """
        WITH stale_pdf AS (
            SELECT att.id
              FROM ir_attachment att
              JOIN account_move move
                ON move.id = att.res_id
             WHERE att.res_model = 'account.move'
               AND att.res_field = 'invoice_pdf_report_file'
               AND move.move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
        )
        UPDATE account_move move
           SET message_main_attachment_id = NULL
         WHERE move.message_main_attachment_id IN (SELECT id FROM stale_pdf)
        """
    )
    cr.execute(
        """
        DELETE FROM ir_attachment att
         USING account_move move
         WHERE move.id = att.res_id
           AND att.res_model = 'account.move'
           AND att.res_field = 'invoice_pdf_report_file'
           AND move.move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
        """
    )
