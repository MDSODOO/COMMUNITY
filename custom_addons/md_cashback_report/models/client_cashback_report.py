# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ClientCashbackReport(models.Model):
    # Alcance PROSPECTIVO: solo agrega líneas de factura posteadas que ya
    # traen un descuento por línea (discount > 0) para clientes marcados con
    # x_cashback_split_scheme=True. El 5% de cashback se calcula sobre el
    # monto base (antes de descuento), por lo que 2% + 5% = 7% del monto
    # base cuando el 2% se aplica de forma consistente.
    _name = 'client.cashback.report'
    _description = 'Trazabilidad Descuento 2% + Cashback 5%'
    _auto = False
    _order = 'invoice_month desc, company_id, partner_id'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    company_id = fields.Many2one('res.company', string='Sucursal', readonly=True)
    invoice_month = fields.Date(string='Mes', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    invoice_count = fields.Integer(string='# Facturas', readonly=True)

    base_amount = fields.Monetary(
        string='Monto Base', readonly=True, currency_field='currency_id',
        help='Suma de price_unit x quantity antes de cualquier descuento.',
    )
    discount_amount = fields.Monetary(
        string='Descuento Aplicado (2%)', readonly=True, currency_field='currency_id',
        help='Descuento realmente capturado por línea en factura.',
    )
    invoiced_total = fields.Monetary(
        string='Total Facturado', readonly=True, currency_field='currency_id',
        help='Total de factura (price_total), ya con el descuento e impuestos aplicados.',
    )
    cashback_provision = fields.Monetary(
        string='Provisión Cashback (5%)', readonly=True, currency_field='currency_id',
        help='5% del Monto Base a devolver en efectivo a fin de mes.',
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW client_cashback_report AS (
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY am.partner_id, am.company_id, DATE_TRUNC('month', am.invoice_date)
                    )::integer                                         AS id,
                    am.partner_id                                      AS partner_id,
                    am.company_id                                      AS company_id,
                    DATE_TRUNC('month', am.invoice_date)::date         AS invoice_month,
                    am.currency_id                                     AS currency_id,
                    COUNT(DISTINCT am.id)                              AS invoice_count,
                    SUM(aml.price_unit * aml.quantity)                 AS base_amount,
                    SUM(aml.price_unit * aml.quantity * aml.discount / 100.0)
                                                                        AS discount_amount,
                    SUM(aml.price_total)                               AS invoiced_total,
                    SUM(aml.price_unit * aml.quantity) * 0.05          AS cashback_provision
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                JOIN res_partner rp ON rp.id = am.partner_id
                WHERE am.move_type = 'out_invoice'
                  AND am.state = 'posted'
                  AND aml.display_type = 'product'
                  AND aml.discount > 0
                  AND rp.x_cashback_split_scheme = TRUE
                GROUP BY
                    am.partner_id, am.company_id,
                    DATE_TRUNC('month', am.invoice_date), am.currency_id
            )
        """)
