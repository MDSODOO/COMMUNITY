# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ClientCashbackReport(models.Model):
    # Alcance PROSPECTIVO: solo agrega líneas de factura posteadas para
    # clientes marcados con x_cashback_split_scheme=True. El 5% de cashback
    # se calcula sobre el monto base (antes de descuento), por lo que
    # 2% + 5% = 7% del monto base cuando el 2% se aplica de forma
    # consistente.
    #
    # EXCLUSIÓN DE PRODUCTOS: las líneas cuyo producto está en la lista
    # res.partner.x_cashback_excluded_product_ids del cliente de la factura
    # se apartan por completo del cálculo base (no cuentan para
    # base_amount/discount_amount/cashback_provision/cashback_real ni para
    # anomaly_line_count), pero sí se reportan en gross_invoiced_total y en
    # excluded_base_amount/excluded_total para trazabilidad del desglose.
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

    gross_invoiced_total = fields.Monetary(
        string='Total Facturado', readonly=True, currency_field='currency_id',
        help='Total de factura (price_total) de TODAS las líneas de producto '
             'del cliente en el mes, sin importar si llevan descuento o si '
             'el producto está excluido de cashback. Cifra de referencia '
             'para conciliar contra la Base Neta Computable.',
    )
    excluded_base_amount = fields.Monetary(
        string='Monto Base Excluido', readonly=True, currency_field='currency_id',
        help='Suma de price_unit x quantity de líneas cuyo producto está en '
             'la lista de productos excluidos de cashback del cliente '
             '(res.partner.x_cashback_excluded_product_ids). No participa '
             'en el cálculo de descuento ni de cashback.',
    )
    excluded_total = fields.Monetary(
        string='Total Facturado Excluido', readonly=True, currency_field='currency_id',
        help='Total de factura (price_total, con impuestos) de las líneas '
             'de productos excluidos de cashback.',
    )
    base_amount = fields.Monetary(
        string='Base Neta Computable', readonly=True, currency_field='currency_id',
        help='Suma de price_unit x quantity, antes de descuento, de líneas '
             'CON el 2% capturado y de productos NO excluidos. Es la base '
             'real sobre la que se calcula el 5% de cashback.',
    )
    discount_amount = fields.Monetary(
        string='Descuento Aplicado (2%)', readonly=True, currency_field='currency_id',
        help='Descuento realmente capturado por línea en factura, en '
             'líneas de productos no excluidos.',
    )
    invoiced_total = fields.Monetary(
        string='Total Facturado (líneas con 2%)', readonly=True, currency_field='currency_id',
        help='Total de factura (price_total) de las líneas no excluidas '
             'donde ya se capturó el 2% de descuento.',
    )
    cashback_provision = fields.Monetary(
        string='Provisión Cashback (5%) Teórica', readonly=True, currency_field='currency_id',
        help='5% de la Base Neta Computable (líneas no excluidas con 2% '
             'capturado). Ya excluye productos no elegibles.',
    )
    cashback_real = fields.Monetary(
        string='Cashback Real (5% sobre 2% capturado)', readonly=True, currency_field='currency_id',
        help='5% calculado únicamente sobre las líneas no excluidas donde '
             'se aplicó el 2% correctamente. Si difiere de la Provisión '
             'Teórica, hay líneas con descuento omitido.',
    )
    anomaly_line_count = fields.Integer(
        string='Líneas con Descuento Incorrecto',  readonly=True,
        help='Cantidad de líneas de producto NO excluido en este mes donde '
             'el descuento no fue exactamente 2%. Ver reporte Anomalías '
             'Cashback para el detalle.',
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

                    -- Total facturado bruto: TODAS las líneas de producto,
                    -- excluidas o no, con o sin descuento.
                    SUM(aml.price_total)                               AS gross_invoiced_total,

                    -- Desglose de lo excluido (para trazabilidad).
                    SUM(
                        CASE WHEN excl.product_id IS NOT NULL
                            THEN aml.price_unit * aml.quantity
                            ELSE 0
                        END
                    )                                                   AS excluded_base_amount,
                    SUM(
                        CASE WHEN excl.product_id IS NOT NULL
                            THEN aml.price_total
                            ELSE 0
                        END
                    )                                                   AS excluded_total,

                    -- A partir de aquí, SOLO líneas de productos NO excluidos
                    -- y con el 2% ya capturado (discount > 0) — base neta
                    -- computable para el esquema 2% + 5%.
                    SUM(
                        CASE WHEN excl.product_id IS NULL AND aml.discount > 0
                            THEN aml.price_unit * aml.quantity
                            ELSE 0
                        END
                    )                                                   AS base_amount,
                    SUM(
                        CASE WHEN excl.product_id IS NULL AND aml.discount > 0
                            THEN aml.price_unit * aml.quantity * aml.discount / 100.0
                            ELSE 0
                        END
                    )                                                   AS discount_amount,
                    SUM(
                        CASE WHEN excl.product_id IS NULL AND aml.discount > 0
                            THEN aml.price_total
                            ELSE 0
                        END
                    )                                                   AS invoiced_total,
                    -- Provisión teórica: 5% de la base neta computable.
                    SUM(
                        CASE WHEN excl.product_id IS NULL AND aml.discount > 0
                            THEN aml.price_unit * aml.quantity
                            ELSE 0
                        END
                    ) * 0.05                                            AS cashback_provision,
                    -- Cashback real: 5% solo sobre líneas no excluidas donde
                    -- el 2% fue aplicado exactamente.
                    SUM(
                        CASE WHEN excl.product_id IS NULL AND aml.discount = 2.0
                            THEN aml.price_unit * aml.quantity * 0.05
                            ELSE 0
                        END
                    )                                                   AS cashback_real,
                    -- Líneas NO excluidas con discount <> 2% (anomalías reales).
                    COUNT(aml.id) FILTER (
                        WHERE excl.product_id IS NULL AND aml.discount <> 2.0
                    )                                                   AS anomaly_line_count
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                JOIN res_partner rp ON rp.id = am.partner_id
                LEFT JOIN res_partner_cashback_excluded_product_rel excl
                       ON excl.partner_id = rp.id
                      AND excl.product_id = aml.product_id
                WHERE am.move_type = 'out_invoice'
                  AND am.state = 'posted'
                  AND aml.display_type = 'product'
                  AND rp.x_cashback_split_scheme = TRUE
                GROUP BY
                    am.partner_id, am.company_id,
                    DATE_TRUNC('month', am.invoice_date), am.currency_id
            )
        """)


class ClientCashbackAnomaly(models.Model):
    """Vista de anomalías: líneas de producto para clientes del esquema cashback
    donde el descuento es 0% (línea sin descuento capturado).  Permite al equipo
    de finanzas/ventas identificar qué facturas/productos requieren corrección
    antes del cierre de mes, y al flujo n8n detectarlas y notificar automáticamente.
    """
    _name = 'client.cashback.anomaly'
    _description = 'Anomalías de Descuento — Clientes Cashback'
    _auto = False
    _order = 'invoice_date desc, partner_id, move_name'
    _rec_name = 'move_name'

    partner_id      = fields.Many2one('res.partner',  string='Cliente',   readonly=True)
    company_id      = fields.Many2one('res.company',  string='Sucursal',  readonly=True)
    move_name       = fields.Char(string='Factura',   readonly=True)
    invoice_date    = fields.Date(string='Fecha',     readonly=True)
    invoice_month   = fields.Date(string='Mes',       readonly=True)
    currency_id     = fields.Many2one('res.currency', string='Moneda',    readonly=True)
    product_id      = fields.Many2one('product.product', string='Producto', readonly=True)
    product_name    = fields.Char(string='Descripción de línea', readonly=True)
    quantity        = fields.Float(string='Cantidad',  readonly=True)
    price_unit      = fields.Float(string='P. Unit.',  readonly=True)
    discount        = fields.Float(string='Desc. %',   readonly=True)
    base_amount     = fields.Monetary(
        string='Monto Base', readonly=True, currency_field='currency_id',
        help='price_unit x quantity de esta línea (sin descuento).'
    )
    cashback_missed = fields.Monetary(
        string='Cashback 5% No Capturado', readonly=True, currency_field='currency_id',
        help='5% del monto base de esta línea que no se acumula en el reporte '
             'porque el descuento no fue capturado.'
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW client_cashback_anomaly AS (
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY am.partner_id, am.company_id, am.invoice_date, aml.id
                    )::integer                                          AS id,
                    am.partner_id                                       AS partner_id,
                    am.company_id                                       AS company_id,
                    am.name                                             AS move_name,
                    am.invoice_date                                     AS invoice_date,
                    DATE_TRUNC('month', am.invoice_date)::date          AS invoice_month,
                    am.currency_id                                      AS currency_id,
                    aml.product_id                                      AS product_id,
                    aml.name                                            AS product_name,
                    aml.quantity                                        AS quantity,
                    aml.price_unit                                      AS price_unit,
                    aml.discount                                        AS discount,
                    (aml.price_unit * aml.quantity)                     AS base_amount,
                    (aml.price_unit * aml.quantity * 0.05)              AS cashback_missed
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                JOIN res_partner rp ON rp.id = am.partner_id
                LEFT JOIN res_partner_cashback_excluded_product_rel excl
                       ON excl.partner_id = rp.id
                      AND excl.product_id = aml.product_id
                WHERE am.move_type = 'out_invoice'
                  AND am.state = 'posted'
                  AND aml.display_type = 'product'
                  AND aml.discount = 0          -- solo líneas SIN descuento
                  AND rp.x_cashback_split_scheme = TRUE  -- solo clientes del esquema
                  AND excl.product_id IS NULL   -- excluye productos no elegibles: no es anomalía
            )
        """)
