import logging
import random
import re
import unicodedata

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RaffleCampaign(models.Model):
    _name = 'raffle.campaign'
    _description = 'Campaña de Rifa'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nombre', required=True, tracking=True)
    code = fields.Char(
        string='Código', required=True, tracking=True, readonly=True,
        help='Código corto de la campaña usado como prefijo del folio '
             '(ej. "52A" para 52 Aniversario → folio "52A-R-000123"). '
             'Se genera automáticamente a partir del nombre al crear la '
             'campaña — así el cliente identifica de un vistazo a qué rifa '
             'pertenece su boleto, sin depender de que alguien lo escriba '
             'bien a mano.',
    )
    date_start = fields.Date(string='Fecha de Inicio', required=True, tracking=True)
    date_end = fields.Date(string='Fecha de Fin', required=True, tracking=True)
    date_draw = fields.Datetime(string='Fecha del Sorteo', tracking=True)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('active', 'Activa'),
        ('closed', 'Cerrada (sin sorteo)'),
        ('drawn', 'Sorteada'),
    ], string='Estado', default='draft', required=True, tracking=True)

    rule_ids = fields.One2many('raffle.rule', 'campaign_id', string='Reglas de Premiación')
    ticket_ids = fields.One2many('raffle.ticket', 'campaign_id', string='Folios')
    ticket_count = fields.Integer(string='Cantidad de Folios', compute='_compute_ticket_count')

    prize_ids = fields.One2many('raffle.prize', 'campaign_id', string='Premios')
    prize_count = fields.Integer(string='Cantidad de Premios', compute='_compute_prize_count')

    daily_ticket_limit = fields.Integer(
        string='Límite diario de boletos por cliente',
        default=10,
        help='Máximo de boletos que un cliente puede acumular en un mismo día.'
    )

    partner_summary_count = fields.Integer(
        string='Clientes con Boletos', compute='_compute_partner_summary_count')

    winner_ticket_id = fields.Many2one(
        'raffle.ticket', string='Último Boleto Ganador', readonly=True, copy=False,
        help='Último boleto ganador sorteado en esta campaña. El histórico '
             'completo por unidad de premio vive en prize_ids.winner_ids '
             '(raffle.prize.winner).',
    )
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda s: s.env.company)
    active = fields.Boolean(string='Activo', default=True)

    sequence_physical_id = fields.Many2one(
        'ir.sequence', string='Secuencia Folio Físico', readonly=True, copy=False)
    sequence_online_id = fields.Many2one(
        'ir.sequence', string='Secuencia Folio B2B Online', readonly=True, copy=False)

    _code_uniq = models.Constraint(
        "UNIQUE(code)", "Ya existe una campaña con ese código."
    )

    @api.depends('ticket_ids')
    def _compute_ticket_count(self):
        for camp in self:
            camp.ticket_count = len(camp.ticket_ids)

    @api.depends('prize_ids')
    def _compute_prize_count(self):
        for camp in self:
            camp.prize_count = len(camp.prize_ids)

    @api.depends('ticket_ids')
    def _compute_partner_summary_count(self):
        Summary = self.env['raffle.ticket.summary']
        for camp in self:
            camp.partner_summary_count = Summary.search_count(
                [('campaign_id', '=', camp.id)]
            )

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for camp in self:
            if camp.date_start and camp.date_end and camp.date_start > camp.date_end:
                raise UserError('La fecha de inicio no puede ser posterior a la fecha de fin.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code'):
                vals['code'] = vals['code'].strip().upper()
            else:
                vals['code'] = self._generate_code(vals.get('name'))
        campaigns = super().create(vals_list)
        campaigns._ensure_sequences()
        return campaigns

    def _generate_code(self, name):
        """Deriva un código corto (ej. "52ANIV") a partir del nombre de la
        campaña, único entre campañas. El usuario nunca lo escribe a mano:
        se calcula aquí y el campo queda readonly en el formulario."""
        normalized = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode()
        base = re.sub(r'[^A-Za-z0-9]', '', normalized).upper()[:6] or 'RIFA'

        code = base
        suffix = 1
        while self.search_count([('code', '=', code)]):
            suffix += 1
            str_suffix = str(suffix)
            code = base[:6 - len(str_suffix)] + str_suffix
        return code

    def _ensure_sequences(self):
        """Aprovisiona las secuencias de folio (una por canal) la primera
        vez que se necesitan. Cada campaña reinicia su propio consecutivo
        — dos campañas distintas nunca comparten numeración — y el código
        de campaña queda embebido en el prefijo (ej. "52A-R-000123"),
        así el folio es autodescriptivo sin tener que consultar el sistema."""
        Sequence = self.env['ir.sequence'].sudo()
        for campaign in self:
            if not campaign.sequence_physical_id:
                campaign.sequence_physical_id = Sequence.create({
                    'name': 'Rifa %s - Folio Físico' % campaign.name,
                    'prefix': '%s-R-' % campaign.code,
                    'padding': 6,
                    'company_id': False,
                })
            if not campaign.sequence_online_id:
                campaign.sequence_online_id = Sequence.create({
                    'name': 'Rifa %s - Folio B2B Online' % campaign.name,
                    'prefix': '%s-BP-' % campaign.code,
                    'padding': 6,
                    'company_id': False,
                })

    def action_activate(self):
        self.write({'state': 'active'})

    def action_close(self):
        self.write({'state': 'closed'})

    def get_pending_prizes(self):
        """Unidades de premio de esta campaña que aún no tienen ganador, en
        orden de sorteo (premio, luego unidad dentro del premio si
        quantity > 1). Lo consume el frontend OWL (RaffleWheel) para saber
        qué unidad sortear a continuación, una a la vez. Cada entrada trae
        el id de la unidad (raffle.prize.winner, usado para action_draw_winner)
        y el id del premio padre (usado para la imagen)."""
        self.ensure_one()
        result = []
        for prize in self.prize_ids.sorted('sequence'):
            units = prize.winner_ids.sorted('sequence')
            total = len(units)
            for idx, unit in enumerate(units, start=1):
                if unit.ticket_id:
                    continue
                label = prize.name if total <= 1 else '%s (%s/%s)' % (prize.name, idx, total)
                result.append({
                    'id': unit.id,
                    'prize_id': prize.id,
                    'name': label,
                    'has_image': bool(prize.image),
                })
        return result

    def action_draw_winner(self, winner_id):
        """Selección aleatoria server-side para UNA unidad de premio
        específica (raffle.prize.winner). La UI (OWL) solo anima el
        resultado ya decidido aquí — nunca debe confiarse en Math.random()
        del cliente para el resultado del sorteo. Un mismo boleto no puede
        ganar dos unidades de premio de la misma campaña."""
        self.ensure_one()
        if self.state not in ('active', 'closed'):
            raise UserError('La campaña debe estar activa o cerrada para sortear.')

        winner_slot = self.env['raffle.prize.winner'].browse(winner_id)
        if not winner_slot.exists() or winner_slot.campaign_id != self:
            raise UserError('La unidad de premio no pertenece a esta campaña.')
        if winner_slot.ticket_id:
            raise UserError('Esta unidad de premio ya tiene un ganador asignado.')

        if winner_slot.prize_id.is_main_prize:
            already_won_partner_ids = self.env['raffle.prize.winner'].search(
                [('campaign_id', '=', self.id), ('prize_id.is_main_prize', '=', True)]
            ).mapped('partner_id').ids
        else:
            already_won_partner_ids = []

        already_won_ticket_ids = self.env['raffle.prize.winner'].search(
            [('campaign_id', '=', self.id)]
        ).mapped('ticket_id').ids

        valid_tickets = self.ticket_ids.filtered(
            lambda t: t.state == 'valid' 
                      and t.id not in already_won_ticket_ids 
                      and (not already_won_partner_ids or t.partner_id.id not in already_won_partner_ids)
                      and (not t.sale_order_id or t.sale_order_id.state != 'cancel')
                      and (not t.pos_order_id or t.pos_order_id.state != 'cancel')
        )
        if not valid_tickets:
            raise UserError('No hay folios válidos disponibles para sortear (sin premios previos y venta no cancelada).')

        winner = random.SystemRandom().choice(valid_tickets)
        
        origin_ref = ''
        if winner.sale_order_id:
            origin_ref = winner.sale_order_id.name
        elif winner.pos_order_id:
            origin_ref = winner.pos_order_id.name
        elif winner.legacy_ref:
            origin_ref = winner.legacy_ref
            
        winner_slot.write({
            'ticket_id': winner.id, 
            'date_won': fields.Datetime.now(),
            'user_id': self.env.user.id,
            'origin_ref': origin_ref,
        })
        self.winner_ticket_id = winner.id
        remaining = self.env['raffle.prize.winner'].search_count([
            ('campaign_id', '=', self.id), ('ticket_id', '=', False),
        ])
        if not remaining:
            self.state = 'drawn'
        return winner.id

    def action_open_wheel(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'mds_raffle_wheel',
            'name': 'Sorteo - %s' % self.name,
            'params': {'campaign_id': self.id},
        }

    def _evaluate_order_for_tickets(self, order):
        """order: recordset de sale.order o pos.order ya confirmado/pagado."""
        order_date = order.date_order.date() if hasattr(order, 'date_order') and order.date_order else fields.Date.today()
        active_campaigns = self.search([
            ('state', '=', 'active'),
            ('date_start', '<=', order_date),
            ('date_end', '>=', order_date),
        ])
        for campaign in active_campaigns:
            for rule in campaign.rule_ids.filtered('active'):
                tickets_to_award = rule._evaluate(order)
                if tickets_to_award > 0:
                    self.env['raffle.ticket'].sudo()._create_for_order(
                        campaign, rule, order, tickets_to_award
                    )

    def _evaluate_daily_partner_activity(self, partner_id, date, blocks):
        """Consolidador diario: agrupa por cliente para manejar el caso
        de facturas divididas (varios folios el mismo día que, sumados,
        sí alcanzan el umbral). `blocks` es una lista de dicts, uno por
        origen presente ese día para este cliente:
            {
                'origin': 'pos' | 'online_b2b',
                'amount': float,  # suma diaria ya agregada para ese origen
                'product_line_ids': [ids de md.product.line vendidos],
                'sponsor_product_ids': [ids de product.product patrocinados vendidos],
                'legacy_refs': [folios de origen que componen el bloque],
            }
        Se llama tanto desde el backfill de histórico (Excel) como,
        potencialmente, desde un cron diario sobre pedidos en vivo.
        Devuelve el recordset de raffle.ticket creados (vacío si ya
        existían — reimportar el mismo origen no duplica)."""
        self.ensure_one()
        if self.state != 'active' or not (self.date_start <= date <= self.date_end):
            return self.env['raffle.ticket']

        Ticket = self.env['raffle.ticket'].sudo()
        created = Ticket.browse()
        for block in blocks:
            origin = block['origin']
            origin_type = 'physical' if origin == 'pos' else 'online_b2b'
            line_ids = block.get('product_line_ids') or []
            sponsor_ids = block.get('sponsor_product_ids') or []
            legacy_refs = block.get('legacy_refs') or []
            block_key = '-'.join(sorted(legacy_refs)) or ('%s-%s-%s' % (partner_id, date, origin))

            for rule in self.rule_ids.filtered('active'):
                if rule.rule_type == 'daily_threshold':
                    count = rule._evaluate_daily_threshold(origin, block['amount'])
                elif rule.rule_type == 'daily_sponsor_line':
                    count = rule._evaluate_daily_sponsor_line(line_ids)
                elif rule.rule_type == 'daily_sponsor_catalog':
                    count = rule._evaluate_daily_sponsor_catalog(sponsor_ids)
                else:
                    continue
                if count > 0:
                    created |= Ticket._create_for_daily_block(
                        self, rule, partner_id, origin_type, count, block_key, date,
                        amount=block.get('amount') or 0.0, source_refs=legacy_refs,
                    )
        return created

    # --- Integración WhatsApp Business (Meta Cloud API) ---
    # Los tokens viven en res.config.settings (Ajustes > Rifas), respaldados
    # por ir.config_parameter. Sin token/phone_number_id configurados, el
    # envío es un no-op silencioso: no hay credenciales reales todavía, solo
    # se deja preparado el payload y el disparador (ir.cron).

    def _build_whatsapp_payload(self, partner, ticket_count):
        """Payload base para POST a
        https://graph.facebook.com/v20.0/{phone_number_id}/messages,
        usando una plantilla de mensaje ('raffle_ticket_update', a crear
        en Meta Business Manager) con el nombre del cliente y su total de
        boletos acumulados en esta campaña."""
        self.ensure_one()
        # Odoo 19 consolidó res.partner.mobile en el campo phone (ya no
        # existe un campo 'mobile' separado).
        to = (partner.phone or '').strip().replace(' ', '').replace('-', '')
        return {
            'messaging_product': 'whatsapp',
            'to': to,
            'type': 'template',
            'template': {
                'name': 'raffle_ticket_update',
                'language': {'code': 'es_MX'},
                'components': [{
                    'type': 'body',
                    'parameters': [
                        {'type': 'text', 'text': partner.name or ''},
                        {'type': 'text', 'text': str(ticket_count)},
                        {'type': 'text', 'text': self.name or ''},
                    ],
                }],
            },
        }

    def _send_whatsapp_ticket_update(self, partner, ticket_count):
        """Notifica a `partner` por WhatsApp su total de boletos
        acumulados (`ticket_count`) en esta campaña. No-op silencioso si
        el token o el phone_number_id no están configurados en
        Ajustes > Rifas — nunca lanza excepción por falta de credenciales."""
        self.ensure_one()
        icp = self.env['ir.config_parameter'].sudo()
        token = icp.get_param('mds_raffle_campaign.whatsapp_api_token')
        phone_number_id = icp.get_param('mds_raffle_campaign.whatsapp_phone_number_id')
        if not token or not phone_number_id:
            _logger.info(
                'Rifa WhatsApp: notificación omitida para %s (falta configurar '
                'token/phone_number_id en Ajustes > Rifas).', partner.display_name,
            )
            return False
        if not partner.phone:
            _logger.info(
                'Rifa WhatsApp: notificación omitida para %s (sin teléfono registrado).',
                partner.display_name,
            )
            return False

        payload = self._build_whatsapp_payload(partner, ticket_count)
        url = 'https://graph.facebook.com/v20.0/%s/messages' % phone_number_id
        try:
            response = requests.post(
                url, json=payload,
                headers={'Authorization': 'Bearer %s' % token},
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException:
            _logger.exception('Rifa WhatsApp: fallo al notificar a %s', partner.display_name)
            return False
        return True

    @api.model
    def _cron_notify_whatsapp_ticket_updates(self):
        """Disparador asíncrono (ir.cron): revisa boletos creados desde la
        última corrida, los agrupa por cliente+campaña y notifica el total
        acumulado. Avanza el cursor de tiempo solo si llegó a procesar
        (si el token no está configurado, no-op y no mueve el cursor)."""
        icp = self.env['ir.config_parameter'].sudo()
        token = icp.get_param('mds_raffle_campaign.whatsapp_api_token')
        if not token:
            _logger.info('Rifa WhatsApp: cron en no-op, token no configurado en Ajustes > Rifas.')
            return

        last_run = icp.get_param('mds_raffle_campaign.whatsapp_last_run')
        domain = [('state', '=', 'valid')]
        if last_run:
            domain.append(('create_date', '>', last_run))
        tickets = self.env['raffle.ticket'].sudo().search(domain)
        if not tickets:
            return

        groups = {}
        for ticket in tickets:
            groups.setdefault((ticket.partner_id, ticket.campaign_id), 0)
            groups[(ticket.partner_id, ticket.campaign_id)] += 1

        Summary = self.env['raffle.ticket.summary'].sudo()
        for (partner, campaign), _new_count in groups.items():
            summary = Summary.search([
                ('partner_id', '=', partner.id), ('campaign_id', '=', campaign.id),
            ], limit=1)
            total = summary.ticket_count if summary else _new_count
            campaign._send_whatsapp_ticket_update(partner, total)

        icp.set_param('mds_raffle_campaign.whatsapp_last_run', fields.Datetime.now())
