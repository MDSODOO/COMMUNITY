from odoo import api, fields, models


class RaffleTicket(models.Model):
    _name = 'raffle.ticket'
    _description = 'Folio de Rifa'
    _order = 'id desc'

    name = fields.Char(string='Folio', copy=False, index=True)
    campaign_id = fields.Many2one('raffle.campaign', string='Campaña', required=True, ondelete='cascade')
    rule_id = fields.Many2one('raffle.rule', string='Regla que lo generó')
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, index=True)

    origin_type = fields.Selection([
        ('physical', 'Física'),
        ('online_b2b', 'B2B en línea'),
    ], string='Origen', required=True, default='physical')

    sale_order_id = fields.Many2one('sale.order', string='Pedido de Venta')
    pos_order_id = fields.Many2one('pos.order', string='Pedido POS')

    state = fields.Selection([
        ('valid', 'Válido'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='valid')

    legacy_ref = fields.Char(
        string='Referencia legacy',
        help='Traza al origen (ej. folio del sistema/hoja anterior) para '
             'cargas masivas idempotentes: reimportar el mismo archivo no duplica.',
    )

    _name_uniq = models.Constraint(
        "UNIQUE(name)", "Ya existe un folio con ese número."
    )
    _legacy_ref_uniq = models.Constraint(
        "UNIQUE(legacy_ref)", "Ya existe un folio con esa referencia legacy."
    )

    @api.model
    def _create_for_order(self, campaign, rule, order, count):
        origin_type = 'online_b2b' if (
            order._name == 'sale.order' and order.origin_channel == 'b2b_online'
        ) else 'physical'

        vals_list = [{
            'campaign_id': campaign.id,
            'rule_id': rule.id,
            'partner_id': order.partner_id.id,
            'origin_type': origin_type,
            'sale_order_id': order.id if order._name == 'sale.order' else False,
            'pos_order_id': order.id if order._name == 'pos.order' else False,
        } for _ in range(count)]
        return self.create(vals_list)

    @api.model
    def _create_for_daily_block(self, campaign, rule, partner_id, origin_type, count, block_key):
        """Crea hasta `count` boletos para un bloque diario ya agregado
        por raffle.campaign._evaluate_daily_partner_activity (sin
        sale_order_id/pos_order_id: el bloque puede sumar varios folios).
        `block_key` identifica el bloque (típicamente los folios que lo
        componen); cada boleto individual se traza con
        legacy_ref='<block_key>-<rule.id>-<n>'. Reimportar el mismo
        origen no duplica: si ese legacy_ref ya existe, se omite."""
        refs = ['%s-%s-%s' % (block_key, rule.id, n) for n in range(1, count + 1)]
        existing = set(self.search([('legacy_ref', 'in', refs)]).mapped('legacy_ref'))
        vals_list = [{
            'campaign_id': campaign.id,
            'rule_id': rule.id,
            'partner_id': partner_id,
            'origin_type': origin_type,
            'legacy_ref': ref,
        } for ref in refs if ref not in existing]
        return self.create(vals_list) if vals_list else self.browse()

    @api.model_create_multi
    def create(self, vals_list):
        # La secuencia vive en la campaña (no es global): cada campaña
        # numera su propio folio desde 1, con su código embebido en el
        # prefijo (ej. "52A-R-000123"). _ensure_sequences() la crea la
        # primera vez que se necesita (cubre también campañas creadas
        # antes de que este mecanismo existiera).
        campaign_ids = {
            vals['campaign_id'] for vals in vals_list
            if not vals.get('name') and vals.get('campaign_id')
        }
        campaigns = self.env['raffle.campaign'].browse(campaign_ids)
        campaigns._ensure_sequences()
        campaigns_by_id = {c.id: c for c in campaigns}

        for vals in vals_list:
            if not vals.get('name'):
                campaign = campaigns_by_id.get(vals.get('campaign_id'))
                sequence = (
                    campaign.sequence_online_id if vals.get('origin_type') == 'online_b2b'
                    else campaign.sequence_physical_id
                )
                vals['name'] = sequence.next_by_id()
        return super().create(vals_list)
