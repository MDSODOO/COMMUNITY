from odoo import fields, models, tools


class RaffleTicketSummary(models.Model):
    _name = 'raffle.ticket.summary'
    _description = 'Resumen de Boletos por Cliente (Rifa)'
    _auto = False
    _order = 'ticket_count desc'

    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    campaign_id = fields.Many2one('raffle.campaign', string='Campaña', readonly=True)
    ticket_count = fields.Integer(string='Boletos', readonly=True)
    physical_count = fields.Integer(string='Boletos físicos (R)', readonly=True)
    online_count = fields.Integer(string='Boletos web (BP)', readonly=True)
    legacy_refs = fields.Char(string='Folios de origen', readonly=True)
    has_sponsor_line = fields.Boolean(string='Bono línea patrocinadora', readonly=True)
    has_sponsor_catalog = fields.Boolean(string='Bono catálogo patrocinado', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER (ORDER BY t.partner_id, t.campaign_id) AS id,
                    t.partner_id AS partner_id,
                    t.campaign_id AS campaign_id,
                    count(*) AS ticket_count,
                    count(*) FILTER (WHERE t.origin_type = 'physical') AS physical_count,
                    count(*) FILTER (WHERE t.origin_type = 'online_b2b') AS online_count,
                    string_agg(
                        DISTINCT t.legacy_ref, ', ' ORDER BY t.legacy_ref
                    ) FILTER (WHERE t.legacy_ref IS NOT NULL) AS legacy_refs,
                    bool_or(r.rule_type = 'daily_sponsor_line') AS has_sponsor_line,
                    bool_or(r.rule_type = 'daily_sponsor_catalog') AS has_sponsor_catalog
                FROM raffle_ticket t
                LEFT JOIN raffle_rule r ON r.id = t.rule_id
                WHERE t.state = 'valid'
                GROUP BY t.partner_id, t.campaign_id
            )
        """ % self._table)
