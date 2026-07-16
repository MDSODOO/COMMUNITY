# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class MedicineDepotScrapSummary2025(models.Model):
    _name = 'medicine.depot.scrap.summary.2025'
    _description = 'Dashboard dinámico de bajas por sucursal y mes'
    _auto = False
    _table = 'stock_scrap_batch_summary_dashboard'
    _order = 'anio desc, mes, sucursal'
    _rec_name = 'sucursal'

    company_id = fields.Many2one('res.company', string='Compañía', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )
    location_id = fields.Many2one('stock.location', string='Ubicación Física', readonly=True)
    sucursal = fields.Char(string='Sucursal', readonly=True)
    anio = fields.Integer(string='Año', readonly=True)
    mes = fields.Selection(
        [
            ('01', 'Enero'),
            ('02', 'Febrero'),
            ('03', 'Marzo'),
            ('04', 'Abril'),
            ('05', 'Mayo'),
            ('06', 'Junio'),
            ('07', 'Julio'),
            ('08', 'Agosto'),
            ('09', 'Septiembre'),
            ('10', 'Octubre'),
            ('11', 'Noviembre'),
            ('12', 'Diciembre'),
        ],
        string='Mes',
        readonly=True,
    )
    periodo = fields.Date(string='Periodo', readonly=True)
    line_count = fields.Integer(string='Líneas', readonly=True)
    scrap_qty = fields.Float(
        string='Cantidad',
        digits='Product Unit of Measure',
        readonly=True,
    )
    costo = fields.Monetary(
        string='Costo (MXN)',
        currency_field='currency_id',
        readonly=True,
    )

    def init(self):
        # Purga ir.model.data huérfanos de la importación previa por CSV.
        # Antes el modelo era una tabla real con datos estáticos; al pasar
        # a vista SQL agregada, esos XMLIDs apuntan a "filas" no eliminables
        # y reventaban con ObjectNotInPrerequisiteState en cada upgrade.
        self.env.cr.execute("""
            DELETE FROM ir_model_data
            WHERE module = 'medicine_depot_scrap_batch'
              AND model  = 'medicine.depot.scrap.summary.2025'
        """)

        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = %s
                  AND column_name = %s
                LIMIT 1
            """,
            ('stock_scrap_batch_line', 'scrap_total_cost'),
        )
        has_scrap_total_cost = bool(self.env.cr.fetchone())
        batch_line_join = (
            "LEFT JOIN stock_scrap_batch_line l ON l.scrap_id = s.id"
            if has_scrap_total_cost
            else ""
        )
        batch_line_total_expr = (
            "l.scrap_total_cost"
            if has_scrap_total_cost
            else "NULL"
        )
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                -- Tabla de precios unitarios por lote (primera entrada de PO)
                -- usada para enriquecer bajas legacy sin batch_line asociada.
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
                ),
                base AS (
                    -- Fuente unificada: TODAS las bajas done en stock_scrap.
                    -- Si vinieron del módulo batch, usamos su costo precomputado
                    -- (UoM/currency aware). Si son legacy, calculamos vía PO.
                    SELECT
                        s.company_id,
                        s.location_id,
                        COALESCE(loc.complete_name, loc.name, 'Sin sucursal') AS sucursal,
                        s.date_done AS event_date,
                        s.scrap_qty,
                        COALESCE(
                            {batch_line_total_expr},
                            lc.price_unit * s.scrap_qty,
                            0.0
                        ) AS scrap_total_cost
                    FROM stock_scrap s
                    LEFT JOIN stock_location loc ON loc.id = s.location_id
                    {batch_line_join}
                    LEFT JOIN lot_cost lc
                        ON lc.lot_id = s.lot_id
                       AND lc.product_id = s.product_id
                       AND lc.company_id = s.company_id
                    WHERE s.state = 'done'
                      AND s.date_done IS NOT NULL
                )
                SELECT
                    row_number() OVER (
                        ORDER BY
                            company_id,
                            EXTRACT(YEAR FROM event_date) DESC,
                            TO_CHAR(event_date, 'MM'),
                            sucursal
                    ) AS id,
                    company_id,
                    location_id,
                    sucursal,
                    EXTRACT(YEAR FROM event_date)::integer AS anio,
                    TO_CHAR(event_date, 'MM') AS mes,
                    DATE_TRUNC('month', event_date)::date AS periodo,
                    COUNT(*)::integer AS line_count,
                    SUM(scrap_qty)::double precision AS scrap_qty,
                    SUM(scrap_total_cost)::double precision AS costo
                FROM base
                GROUP BY
                    company_id,
                    location_id,
                    sucursal,
                    EXTRACT(YEAR FROM event_date),
                    TO_CHAR(event_date, 'MM'),
                    DATE_TRUNC('month', event_date)
            )
        """)

    def unlink(self):
        # Modelo analítico (_auto=False) respaldado por SQL VIEW agregada.
        # En upgrades, ir.model_data puede intentar unlink de XMLIDs viejos:
        # evitamos DELETE sobre la vista (no updatable) y tratamos el unlink
        # como no-op seguro.
        return True
