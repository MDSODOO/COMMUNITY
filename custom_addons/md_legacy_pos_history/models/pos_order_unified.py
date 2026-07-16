from odoo import fields, models, tools


class MdPosOrderUnified(models.Model):
    _name = "md.pos.order.unified"
    _description = "Histórico PoS unificado (actual + legado, solo lectura)"
    _auto = False
    _order = "order_date desc"
    _rec_name = "folio"

    source = fields.Selection(
        [("real", "Actual (Odoo)"), ("legacy", "Histórico (Microsip)")],
        string="Origen", readonly=True,
    )
    folio = fields.Char(string="Folio", readonly=True)
    order_date = fields.Date(string="Fecha", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Cliente", readonly=True)
    company_id = fields.Many2one("res.company", string="Sucursal", readonly=True)
    amount_total = fields.Monetary(string="Total", readonly=True)
    state = fields.Selection(
        [("normal", "Normal"), ("cancelado", "Cancelado"), ("otro", "Otro")],
        string="Estado", readonly=True,
    )
    currency_id = fields.Many2one("res.currency", string="Moneda", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW md_pos_order_unified AS (
                SELECT
                    po.id AS id,
                    'real' AS source,
                    po.name AS folio,
                    po.date_order::date AS order_date,
                    po.partner_id AS partner_id,
                    po.company_id AS company_id,
                    po.amount_total AS amount_total,
                    CASE WHEN po.state = 'cancel' THEN 'cancelado' ELSE 'normal' END AS state,
                    rc.currency_id AS currency_id
                FROM pos_order po
                LEFT JOIN res_company rc ON rc.id = po.company_id
                UNION ALL
                SELECT
                    lpo.id + 100000000 AS id,
                    'legacy' AS source,
                    lpo.folio AS folio,
                    lpo.date AS order_date,
                    lpo.partner_id AS partner_id,
                    lpo.company_id AS company_id,
                    lpo.amount_total AS amount_total,
                    lpo.state AS state,
                    lpo.currency_id AS currency_id
                FROM md_legacy_pos_order lpo
            )
        """)
