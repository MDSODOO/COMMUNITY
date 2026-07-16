# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class MedicineDepotScrapHistoryLegacy(models.Model):
    _name = 'medicine.depot.scrap.history'
    _description = 'Historial legado de bajas'
    _rec_name = 'name'
    _auto = False
    _table = 'stock_scrap_batch_history'
    _order = 'date_done desc, id desc'

    name = fields.Char(readonly=True)
    date_done = fields.Datetime(readonly=True)
    create_uid = fields.Many2one('res.users', readonly=True)
    create_date = fields.Datetime(readonly=True)
    product_id = fields.Many2one('product.product', readonly=True)
    lot_id = fields.Many2one('stock.lot', readonly=True)
    scrap_qty = fields.Float(readonly=True)
    product_uom_id = fields.Many2one('uom.uom', readonly=True)
    location_id = fields.Many2one('stock.location', readonly=True)
    scrap_location_id = fields.Many2one('stock.location', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    state = fields.Selection([('done', 'Hecho')], readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )
    expiration_date = fields.Datetime(
        related='lot_id.expiration_date',
        string='Caducidad',
        readonly=True,
    )
    # Costo precomputado en la SQL view (no más Python compute por record).
    # Permite usarlo como measure en pivot/graph y agregaciones sum= en list.
    purchase_lot_cost = fields.Monetary(
        string='Costo unitario',
        currency_field='currency_id',
        readonly=True,
    )
    scrap_total_cost = fields.Monetary(
        string='Costo total',
        currency_field='currency_id',
        readonly=True,
    )

    def action_print_legacy_report(self):
        return self.env.ref(
            'medicine_depot_scrap_batch.action_report_medicine_depot_scrap_history'
        ).report_action(self.sorted('id'))

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'medicine_depot_scrap_history')
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = %s
                  AND column_name IN (%s, %s)
            """,
            ('stock_scrap_batch_line', 'purchase_lot_cost', 'scrap_total_cost'),
        )
        line_columns = {row[0] for row in self.env.cr.fetchall()}
        purchase_cost_expr = (
            'bl.purchase_lot_cost'
            if 'purchase_lot_cost' in line_columns
            else 'NULL'
        )
        total_cost_expr = (
            'bl.scrap_total_cost'
            if 'scrap_total_cost' in line_columns
            else 'NULL'
        )
        # stock_scrap está garantizado: 'stock' es dependencia dura del módulo.
        # El guard previo (SELECT 1 FROM information_schema…) podía dropear la
        # vista y no recrearla si el cursor estaba en un estado inesperado,
        # dejando UndefinedTable en producción.
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                WITH lot_cost AS (
                    SELECT DISTINCT ON (sml.lot_id, sm.product_id, sm.company_id)
                        sml.lot_id,
                        sm.product_id,
                        sm.company_id,
                        pol.price_unit
                    FROM stock_move sm
                    JOIN stock_move_line sml ON sml.move_id = sm.id
                    JOIN purchase_order_line pol ON pol.id = sm.purchase_line_id
                    WHERE sm.state = 'done'
                      AND sml.lot_id IS NOT NULL
                    ORDER BY sml.lot_id, sm.product_id, sm.company_id, sm.date ASC
                )
                SELECT
                    row_number() OVER (ORDER BY s.date_done DESC, s.id DESC) AS id,
                    s.name,
                    s.date_done,
                    s.create_uid,
                    s.create_date,
                    s.product_id,
                    s.lot_id,
                    s.scrap_qty,
                    s.product_uom_id,
                    s.location_id,
                    s.scrap_location_id,
                    s.company_id,
                    s.state,
                    COALESCE(
                        {purchase_cost_expr},
                        lc.price_unit,
                        0.0
                    ) AS purchase_lot_cost,
                    COALESCE(
                        {total_cost_expr},
                        lc.price_unit * s.scrap_qty,
                        0.0
                    ) AS scrap_total_cost
                FROM stock_scrap s
                LEFT JOIN stock_scrap_batch_line bl ON bl.scrap_id = s.id
                LEFT JOIN lot_cost lc
                    ON lc.lot_id = s.lot_id
                   AND lc.product_id = s.product_id
                   AND lc.company_id = s.company_id
                WHERE s.state = 'done'
            )
        """)
