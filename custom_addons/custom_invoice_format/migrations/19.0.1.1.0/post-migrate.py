# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Drop stale generated customer-invoice PDFs.

    Odoo stores the rendered invoice in account.move.invoice_pdf_report_file.
    If that attachment already exists, portal/download flows reuse it and do
    not render the updated QWeb. Removing only that generated binary makes the
    next print/download recreate the PDF with the pharma layout.
    """
    cr.execute(
        """
        WITH stale_pdf AS (
            SELECT att.id
              FROM ir_attachment att
              JOIN account_move move
                ON move.id = att.res_id
             WHERE att.res_model = 'account.move'
               AND att.res_field = 'invoice_pdf_report_file'
               AND move.move_type IN ('out_invoice', 'out_refund')
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
           AND move.move_type IN ('out_invoice', 'out_refund')
        """
    )
