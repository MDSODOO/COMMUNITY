from odoo import _, fields, models, tools


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
    legacy_refs = fields.Char(
        string='Folios de origen', readonly=True,
        help='Bloques/pedidos de origen distintos que sustentan los boletos de este '
             'cliente en esta campaña — homologado desde raffle.ticket.calc_source_refs, '
             'no desde legacy_ref crudo: legacy_ref es único POR BOLETO individual (para '
             'la idempotencia de la carga), así que un cliente con 97 boletos del mismo '
             'bloque tendría 97 legacy_ref casi idénticos si se agregaran tal cual — '
             'calc_source_refs ya identifica el bloque/pedido compartido, así que aquí '
             'aparece una sola vez por bloque real, no una vez por boleto.')
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
                        DISTINCT t.calc_source_refs, ', ' ORDER BY t.calc_source_refs
                    ) FILTER (WHERE t.calc_source_refs IS NOT NULL AND t.calc_source_refs != '') AS legacy_refs,
                    bool_or(r.rule_type = 'daily_sponsor_line') AS has_sponsor_line,
                    bool_or(r.rule_type = 'daily_sponsor_catalog') AS has_sponsor_catalog
                FROM raffle_ticket t
                LEFT JOIN raffle_rule r ON r.id = t.rule_id
                WHERE t.state = 'valid'
                GROUP BY t.partner_id, t.campaign_id
            )
        """ % self._table)

    def action_view_tickets(self):
        """Abre el listado de folios (raffle.ticket) de este cliente en
        esta campaña, reutilizando la acción/vistas ya existentes en
        vez de duplicar una lista nueva."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'mds_raffle_campaign.action_raffle_ticket'
        )
        action['domain'] = [
            ('partner_id', '=', self.partner_id.id),
            ('campaign_id', '=', self.campaign_id.id),
        ]
        action['context'] = {}
        name = _('Boletos de %s', self.partner_id.name)
        action['name'] = name
        action['display_name'] = name
        return action
