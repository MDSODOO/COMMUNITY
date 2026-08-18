from odoo import api, fields, models
from odoo.exceptions import UserError


class RafflePrize(models.Model):
    _name = 'raffle.prize'
    _description = 'Premio de Rifa'
    _order = 'campaign_id, sequence, id'

    campaign_id = fields.Many2one('raffle.campaign', string='Campaña', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Orden de Sorteo', default=10)
    name = fields.Char(string='Premio', required=True)
    image = fields.Image(
        string='Imagen del premio', max_width=1024, max_height=1024,
        help='Foto del premio — se muestra en la ruleta al revelar al ganador '
             'y en el listado de ganadores.',
    )
    quantity = fields.Integer(
        string='Cantidad', default=1, required=True,
        help='Unidades idénticas de este premio a sortear (ej. 3 cafeteras '
             'iguales → 3 ganadores distintos para "Cafetera", sin tener que '
             'crear 3 filas repetidas). Cada unidad se sortea por separado '
             '("Revelar al siguiente ganador" avanza unidad por unidad).',
    )

    winner_ids = fields.One2many('raffle.prize.winner', 'prize_id', string='Ganadores')
    winner_count = fields.Integer(string='Unidades sorteadas', compute='_compute_winner_count', store=True)
    progress = fields.Char(string='Progreso', compute='_compute_winner_count', store=True)

    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('partial', 'Parcial'),
        ('awarded', 'Entregado'),
    ], string='Estado', compute='_compute_winner_count', store=True)

    is_main_prize = fields.Boolean(
        string='Es Premio Principal', default=True,
        help='Si está marcado, un mismo cliente no podrá ganar más de un premio principal en la misma campaña.'
    )

    @api.depends('winner_ids.ticket_id', 'quantity')
    def _compute_winner_count(self):
        for prize in self:
            won = len(prize.winner_ids.filtered('ticket_id'))
            prize.winner_count = won
            prize.progress = '%s/%s' % (won, prize.quantity)
            if won == 0:
                prize.state = 'pending'
            elif won < prize.quantity:
                prize.state = 'partial'
            else:
                prize.state = 'awarded'

    @api.constrains('quantity')
    def _check_quantity(self):
        for prize in self:
            if prize.quantity < 1:
                raise UserError('La cantidad debe ser al menos 1.')

    @api.model_create_multi
    def create(self, vals_list):
        prizes = super().create(vals_list)
        prizes._sync_winner_slots()
        return prizes

    def write(self, vals):
        res = super().write(vals)
        if 'quantity' in vals:
            self._sync_winner_slots()
        return res

    def _sync_winner_slots(self):
        """Mantiene raffle.prize.winner en sincronía con `quantity`: crea las
        unidades ("slots") que falten y, si se reduce la cantidad, borra
        solo las unidades aún sin ganador (nunca una ya sorteada)."""
        Winner = self.env['raffle.prize.winner']
        for prize in self:
            current = len(prize.winner_ids)
            missing = prize.quantity - current
            if missing > 0:
                Winner.create([
                    {'prize_id': prize.id, 'sequence': (current + i + 1) * 10}
                    for i in range(missing)
                ])
            elif missing < 0:
                removable = prize.winner_ids.filtered(lambda w: not w.ticket_id) \
                    .sorted('sequence', reverse=True)[:abs(missing)]
                if len(removable) < abs(missing):
                    raise UserError(
                        'No se puede reducir la cantidad de "%s" por debajo del '
                        'número de unidades que ya tienen ganador.' % prize.name
                    )
                removable.unlink()


class RafflePrizeWinner(models.Model):
    _name = 'raffle.prize.winner'
    _description = 'Unidad de Premio Sorteada'
    _order = 'prize_id, sequence, id'

    prize_id = fields.Many2one('raffle.prize', string='Premio', required=True, ondelete='cascade')
    campaign_id = fields.Many2one(
        related='prize_id.campaign_id', string='Campaña', store=True, readonly=True,
    )
    sequence = fields.Integer(string='Unidad #', default=10)

    ticket_id = fields.Many2one(
        'raffle.ticket', string='Boleto Ganador', readonly=True, copy=False,
        help='Se asigna al sortear esta unidad (raffle.campaign.action_draw_winner) '
             'y queda como registro histórico permanente de quién la ganó.',
    )
    partner_id = fields.Many2one(
        related='ticket_id.partner_id', string='Ganador', store=True, readonly=True,
    )
    date_won = fields.Datetime(string='Fecha de Sorteo', readonly=True, copy=False)
    user_id = fields.Many2one('res.users', string='Usuario que Ejecutó', readonly=True, copy=False)
    origin_ref = fields.Char(string='Folio Origen (Venta)', readonly=True, copy=False)

    _ticket_uniq = models.Constraint(
        "UNIQUE(ticket_id)",
        "Este boleto ya fue asignado como ganador de otra unidad de premio.",
    )

    @api.constrains('ticket_id', 'prize_id')
    def _check_ticket_campaign(self):
        for winner in self:
            if winner.ticket_id and winner.ticket_id.campaign_id != winner.prize_id.campaign_id:
                raise UserError(
                    'El boleto ganador debe pertenecer a la misma campaña que el premio.'
                )
