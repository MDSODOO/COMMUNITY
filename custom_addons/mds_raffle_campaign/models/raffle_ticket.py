import logging
import re
from collections import defaultdict
from datetime import datetime, time

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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

    ticket_date = fields.Date(
        string='Fecha de referencia',
        default=fields.Date.context_today,
        help='Fecha de la venta/bloque que originó este folio — se usa para '
             'el límite diario de boletos por cliente. NO usar create_date '
             'para eso: en una carga histórica todos los folios se crean el '
             'mismo día (hoy), así que create_date no distingue a qué fecha '
             'real de venta pertenece cada uno.',
    )

    # --- Auditoría del cálculo (snapshot al momento de la emisión) ---
    # El monto acumulado del día, el multiplicador de canal y los folios
    # que integran un bloque diario son datos TRANSITORIOS: solo existen
    # en memoria mientras raffle.rule._evaluate_daily_threshold() y
    # raffle.campaign._evaluate_daily_partner_activity() corren, y se
    # perdían al terminar la transacción. Estos campos los congelan en el
    # boleto para que la pestaña "Desglose de Cálculo" pueda reconstruir,
    # meses después, por qué se otorgó cada folio — aunque la regla que lo
    # generó cambie o se desactive más adelante.
    currency_id = fields.Many2one(
        'res.currency', related='campaign_id.company_id.currency_id',
        string='Moneda', store=True, readonly=True)
    rule_type = fields.Selection(related='rule_id.rule_type', string='Tipo de regla', store=False, readonly=True)
    rule_tickets_awarded = fields.Integer(
        related='rule_id.tickets_awarded', string='Boletos por unidad (regla actual)', readonly=True,
        help='Valor ACTUAL de rule_id.tickets_awarded — a diferencia de '
             'calc_tickets_awarded, no es un snapshot: si la regla se '
             'edita después, este número cambia con ella.')

    calc_base_amount = fields.Monetary(
        string='Monto base de la regla', currency_field='currency_id', readonly=True,
        help='rule_id.min_amount congelado al momento de emitir el folio (ej. $3,000 MXN).')
    calc_period_amount = fields.Monetary(
        string='Monto acumulado del periodo', currency_field='currency_id', readonly=True,
        help='Para reglas de umbral diario: la suma del día del cliente en ese canal que '
             'disparó la regla. Para reglas por pedido: el total del pedido de venta/POS.')
    calc_tickets_awarded = fields.Integer(
        string='Boletos otorgados en este evento', readonly=True,
        help='Total de boletos que generó el evento de cálculo (pedido o bloque diario) '
             'que incluye este folio — no cambia aunque la regla se edite después.')
    calc_source_refs = fields.Char(
        string='Documentos que integran el cálculo', readonly=True,
        help='Folios/pedidos cuya suma disparó este boleto (para bloques diarios que '
             'combinan varias ventas del mismo cliente en un día).')
    calc_detail = fields.Text(
        string='Detalle del cálculo', readonly=True,
        help='Línea de auditoría legible generada al emitir el folio.')
    calc_confidence = fields.Selection([
        ('exact', 'Exacto'),
        ('estimated', 'Estimado (reconstruido)'),
    ], string='Confiabilidad del monto', readonly=True,
        help='"Exacto": el monto viene de un pedido vinculado, del cálculo en '
             'caliente al emitir el folio, o de un documento de origen '
             'importado del Excel histórico (raffle.source.document). '
             '"Estimado": folio anterior a esta auditoría sin documento de '
             'origen localizado — el monto es el mínimo que explica la '
             'cantidad de boletos otorgados, no el monto real de venta.')

    related_sale_order_ids = fields.Many2many(
        'sale.order', compute='_compute_related_documents',
        string='Pedidos de venta del día')
    related_pos_order_ids = fields.Many2many(
        'pos.order', compute='_compute_related_documents',
        string='Pedidos POS del día')
    source_document_ids = fields.Many2many(
        'raffle.source.document', compute='_compute_source_documents',
        string='Documentos de origen (Excel histórico)',
        help='Resuelto en vivo a partir de calc_source_refs contra '
             'raffle.source.document — si el documento se importa después '
             'de emitido el folio, aparece aquí sin tocar el folio.')

    _name_uniq = models.Constraint(
        "UNIQUE(name)", "Ya existe un folio con ese número."
    )
    _legacy_ref_uniq = models.Constraint(
        "UNIQUE(legacy_ref)", "Ya existe un folio con esa referencia legacy."
    )

    @api.model
    def _get_allowed_ticket_count(self, campaign, partner_id, requested_count, date=None):
        limit = campaign.daily_ticket_limit
        if not limit or limit <= 0:
            return requested_count

        # `date` es la fecha REAL de la venta/bloque (folio físico o B2B),
        # no la fecha de ejecución del script. Usar create_date aquí es un
        # bug: en una carga histórica todos los folios se crean el mismo
        # día (hoy), así que create_date no distingue entre "compró $9,000
        # en un solo día" (debe topar) y "compró $3,000 en 3 días
        # distintos" (no debe topar) — ver ticket_date.
        if date is None:
            date = fields.Date.context_today(self)

        existing_count = self.search_count([
            ('campaign_id', '=', campaign.id),
            ('partner_id', '=', partner_id),
            ('ticket_date', '=', date),
            ('state', '!=', 'cancelled')
        ])

        if existing_count >= limit:
            _logger.info("Cliente %s alcanzó el límite diario (%s) de boletos para la campaña %s en la fecha %s.", partner_id, limit, campaign.id, date)
            return 0

        allowed = min(requested_count, limit - existing_count)
        if allowed < requested_count:
            _logger.info("Cliente %s recibirá %s boletos en vez de %s por límite diario (%s) en la fecha %s.", partner_id, allowed, requested_count, limit, date)

        return allowed

    @api.depends('partner_id', 'ticket_date', 'origin_type', 'sale_order_id', 'pos_order_id')
    def _compute_related_documents(self):
        """No hay FK directa a los documentos que integraron un bloque
        diario (ver _create_for_daily_block): se reconstruyen buscando,
        por cliente/fecha/canal, los pedidos reales que existan en Odoo
        ese día. Para folios de carga histórica cuyo origen solo vive
        como texto en legacy_ref (sin pedido real en este Odoo), la
        búsqueda no encuentra nada — para esos casos, calc_source_refs
        (texto) es la referencia que sí sobrevive."""
        for ticket in self:
            day_start = datetime.combine(ticket.ticket_date, time.min) if ticket.ticket_date else False
            day_end = datetime.combine(ticket.ticket_date, time.max) if ticket.ticket_date else False

            sale_orders = ticket.sale_order_id
            pos_orders = ticket.pos_order_id
            if ticket.partner_id and day_start:
                if ticket.origin_type == 'online_b2b':
                    sale_orders |= self.env['sale.order'].search([
                        ('partner_id', '=', ticket.partner_id.id),
                        ('date_order', '>=', day_start),
                        ('date_order', '<=', day_end),
                        ('state', 'not in', ('draft', 'sent', 'cancel')),
                    ])
                else:
                    pos_orders |= self.env['pos.order'].search([
                        ('partner_id', '=', ticket.partner_id.id),
                        ('date_order', '>=', day_start),
                        ('date_order', '<=', day_end),
                        ('state', '!=', 'cancel'),
                    ])
            ticket.related_sale_order_ids = sale_orders
            ticket.related_pos_order_ids = pos_orders

    @api.model
    def _resolve_source_documents(self, refs_text):
        """refs_text: calc_source_refs de un folio, ej. 'DIARIO-B148212' o,
        para un bloque diario que suma varios folios del mismo cliente,
        'PEDIDOS-R45421-PEDIDOS-R45422' (cada folio individual va
        prefijado con su origen y todos quedan concatenados con '-', sin
        comas — ver block_key en _create_for_daily_block). Se separa
        buscando cada aparición de un prefijo conocido, no por coma, para
        no perder folios cuando el bloque combina más de uno. Resuelve
        contra raffle.source.document (importado del Excel histórico);
        referencias sin match (documento aún no importado, o folio de un
        pedido real de Odoo, no de Excel) se ignoran en silencio."""
        Doc = self.env['raffle.source.document']
        docs = Doc.browse()
        prefix_map = {'DIARIO': 'diario', 'PEDIDOS': 'pedidos'}
        prefixes = '|'.join(prefix_map)
        for ref in re.split(r',\s*|(?=(?:%s)-)' % prefixes, refs_text or ''):
            ref = ref.strip().rstrip('-,').strip()
            if not ref or '-' not in ref:
                continue
            prefix, folio = ref.split('-', 1)
            source_file = prefix_map.get(prefix.upper())
            if not source_file:
                continue
            docs |= Doc.search([('folio', '=', folio), ('source_file', '=', source_file)], limit=1)
        return docs

    @api.depends('calc_source_refs')
    def _compute_source_documents(self):
        for ticket in self:
            ticket.source_document_ids = ticket._resolve_source_documents(ticket.calc_source_refs)

    @api.model
    def _backfill_calc_snapshot(self, ticket_ids=None):
        """_create_for_order/_create_for_daily_block llenan calc_detail y
        compañía en caliente, con el monto exacto del momento — pero eso
        no sirve para folios que YA existían antes de que estos campos
        existieran (ej. los folios de una carga histórica previa). Este
        método reconstruye lo mejor posible a partir del estado actual:
        agrupa boletos "hermanos" del mismo evento (misma campaña+regla+
        cliente+fecha de referencia+pedido, que es como los crea
        _create_for_daily_block/_create_for_order) para recuperar cuántos
        boletos otorgó ese evento, y usa el pedido vinculado (si existe)
        para el monto exacto; si no hay pedido (bloque diario histórico),
        el monto es una ESTIMACIÓN a partir del umbral de la regla — se
        marca como tal en calc_detail, nunca se presenta como el monto
        real original. Idempotente: solo toca folios con calc_detail
        vacío, así que correrlo de nuevo no pisa snapshots ya exactos."""
        domain = [('calc_detail', 'in', (False, ''))]
        if ticket_ids:
            domain.append(('id', 'in', ticket_ids))
        tickets = self.search(domain)
        if not tickets:
            return tickets

        groups = defaultdict(lambda: self.browse())
        for t in tickets:
            key = (t.campaign_id.id, t.rule_id.id, t.partner_id.id, t.ticket_date,
                   t.sale_order_id.id, t.pos_order_id.id)
            groups[key] |= t

        for (campaign_id, rule_id, partner_id, ticket_date, sale_order_id, pos_order_id), group in groups.items():
            rule = self.env['raffle.rule'].browse(rule_id)
            count = len(group)
            order = (
                self.env['sale.order'].browse(sale_order_id) if sale_order_id
                else self.env['pos.order'].browse(pos_order_id) if pos_order_id
                else None
            )
            rule_type_label = dict(rule._fields['rule_type'].selection).get(rule.rule_type, rule.rule_type or 'N/D')
            origin_label = 'físico (POS)' if group[0].origin_type == 'physical' else 'B2B en línea'

            if order:
                period_amount = order.amount_total
                source_refs = order.name
                confidence = 'exact'
                detail = (
                    'Regla "%s" (%s) evaluada sobre el pedido %s (total $%.2f) → '
                    '%s boleto(s) otorgado(s), fecha de referencia %s. '
                    '(Reconstruido a partir del pedido de venta vinculado.)' % (
                        rule.name, rule_type_label, source_refs, period_amount, count, ticket_date,
                    )
                )
            else:
                # legacy_ref tiene forma '<block_key>-<rule.id>-<n>' (ver
                # _create_for_daily_block): quitar el sufijo propio del
                # boleto individual para recuperar el folio/bloque de
                # origen real que comparten todos los hermanos, en vez de
                # listar N variantes casi idénticas del mismo legacy_ref.
                block_keys = set()
                for t in group:
                    if not t.legacy_ref:
                        continue
                    parts = t.legacy_ref.rsplit('-', 2)
                    block_keys.add(parts[0] if len(parts) == 3 else t.legacy_ref)
                source_refs = ', '.join(sorted(block_keys))

                docs = self._resolve_source_documents(source_refs)
                if docs:
                    # Documento real importado del Excel histórico
                    # (raffle.source.document): usar su monto exacto en
                    # vez de la estimación por umbral.
                    period_amount = sum(docs.mapped('amount_total'))
                    confidence = 'exact'
                    detail = (
                        'Regla "%s" (%s): %s boleto(s) otorgado(s) el %s (canal %s), '
                        'monto real $%.2f según documento(s) de origen %s.' % (
                            rule.name, rule_type_label, count, ticket_date, origin_label,
                            period_amount, source_refs,
                        )
                    )
                else:
                    period_amount = (
                        (count / rule.tickets_awarded) * rule.min_amount
                        if rule.tickets_awarded and rule.min_amount else 0.0
                    )
                    confidence = 'estimated'
                    detail = (
                        'Regla "%s" (%s): %s boleto(s) otorgado(s) el %s (canal %s).%s '
                        'Monto acumulado ESTIMADO a partir del umbral de la regla — no '
                        'se localizó el documento de origen para este folio.' % (
                            rule.name, rule_type_label, count, ticket_date, origin_label,
                            ' Folios de origen: %s.' % source_refs if source_refs else '',
                        )
                    )

            group.write({
                'calc_base_amount': rule.min_amount,
                'calc_period_amount': period_amount,
                'calc_tickets_awarded': count,
                'calc_source_refs': source_refs,
                'calc_detail': detail,
                'calc_confidence': confidence,
            })
        return tickets

    @api.model
    def _create_for_order(self, campaign, rule, order, count):
        origin_type = 'online_b2b' if (
            order._name == 'sale.order' and order.origin_channel == 'b2b_online'
        ) else 'physical'

        order_date = order.date_order.date() if getattr(order, 'date_order', False) else fields.Date.context_today(self)

        allowed_count = self._get_allowed_ticket_count(campaign, order.partner_id.id, count, date=order_date)
        if allowed_count <= 0:
            return self.browse()

        detail = (
            'Regla "%s" (%s) evaluada sobre el pedido %s (total $%.2f) → '
            '%s boleto(s) otorgado(s), fecha de referencia %s.' % (
                rule.name, dict(rule._fields['rule_type'].selection).get(rule.rule_type, rule.rule_type),
                order.name, order.amount_total, count, order_date,
            )
        )
        vals_list = [{
            'campaign_id': campaign.id,
            'rule_id': rule.id,
            'partner_id': order.partner_id.id,
            'origin_type': origin_type,
            'sale_order_id': order.id if order._name == 'sale.order' else False,
            'pos_order_id': order.id if order._name == 'pos.order' else False,
            'ticket_date': order_date,
            'calc_base_amount': rule.min_amount,
            'calc_period_amount': order.amount_total,
            'calc_tickets_awarded': count,
            'calc_source_refs': order.name,
            'calc_detail': detail,
            'calc_confidence': 'exact',
        } for _ in range(allowed_count)]
        return self.create(vals_list)

    @api.model
    def _create_for_daily_block(self, campaign, rule, partner_id, origin_type, count, block_key, date,
                                 amount=0.0, source_refs=None):
        """Crea hasta `count` boletos para un bloque diario ya agregado
        por raffle.campaign._evaluate_daily_partner_activity (sin
        sale_order_id/pos_order_id: el bloque puede sumar varios folios).
        `block_key` identifica el bloque (típicamente los folios que lo
        componen); cada boleto individual se traza con
        legacy_ref='<block_key>-<rule.id>-<n>'. Reimportar el mismo
        origen no duplica: si ese legacy_ref ya existe, se omite.
        `date` es la fecha real del bloque (folio físico/B2B) — se guarda
        en ticket_date y es lo que usa el límite diario, no create_date.
        `amount` y `source_refs` son el monto acumulado y los folios de
        origen que ya calculó el llamador (block['amount']/block['legacy_refs']
        en _evaluate_daily_partner_activity) — se guardan tal cual para
        auditoría, no se recalculan aquí."""

        allowed_count = self._get_allowed_ticket_count(campaign, partner_id, count, date=date)
        if allowed_count <= 0:
            return self.browse()

        refs = ['%s-%s-%s' % (block_key, rule.id, n) for n in range(1, allowed_count + 1)]
        existing = set(self.search([('legacy_ref', 'in', refs)]).mapped('legacy_ref'))

        origin_label = 'físico (POS)' if origin_type == 'physical' else 'B2B en línea'
        refs_label = ', '.join(source_refs) if source_refs else ''
        detail = (
            'Regla "%s" (%s): acumulado %s de $%.2f el %s → %s boleto(s) '
            'otorgado(s) en el bloque%s.' % (
                rule.name, dict(rule._fields['rule_type'].selection).get(rule.rule_type, rule.rule_type),
                origin_label, amount, date, count,
                ' (folios: %s)' % refs_label if refs_label else '',
            )
        )
        vals_list = [{
            'campaign_id': campaign.id,
            'rule_id': rule.id,
            'partner_id': partner_id,
            'origin_type': origin_type,
            'legacy_ref': ref,
            'ticket_date': date,
            'calc_base_amount': rule.min_amount,
            'calc_period_amount': amount,
            'calc_tickets_awarded': count,
            'calc_source_refs': refs_label,
            'calc_detail': detail,
            'calc_confidence': 'exact',
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
        tickets = super().create(vals_list)
        tickets._notify_n8n_tickets_created()
        return tickets

    def _notify_n8n_tickets_created(self):
        """Best-effort: notifica al webhook de n8n (evento tickets.created,
        ver docs/n8n_workflows/raffle_whatsapp_README.md) por cada grupo
        (campaña, cliente) recién creado, para que n8n arme y envíe el
        WhatsApp de boletos nuevos. No hace falta cr.commit() antes de
        notificar: a diferencia del webhook de afiliación (que si necesitó
        ese commit porque el receptor vuelve a leer de Odoo), acá el
        payload ya trae todos los datos que n8n necesita — no hay
        read-after-write. Nunca relanza: si el webhook no está configurado
        o falla, solo se loguea, igual que _send_whatsapp_ticket_update."""
        webhook_url = self.env['ir.config_parameter'].sudo().get_param(
            'mds_raffle_campaign.n8n_webhook_url'
        )
        if not webhook_url:
            return

        portal_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        groups = defaultdict(list)
        for ticket in self:
            groups[(ticket.campaign_id, ticket.partner_id)].append(ticket)

        for (campaign, partner), group_tickets in groups.items():
            payload = {
                'event': 'tickets.created',
                'campaign': {
                    'id': campaign.id,
                    'name': campaign.name,
                    'code': campaign.code,
                },
                'partner': {
                    'id': partner.id,
                    'name': partner.name,
                    'phone': partner.phone or '',
                },
                'tickets': {
                    'count': len(group_tickets),
                    'folios': [t.name for t in group_tickets],
                },
                'portal_url': '%s/my/raffles' % portal_base_url,
            }
            try:
                requests.post(webhook_url, json=payload, timeout=5)
            except requests.RequestException:
                _logger.warning(
                    'Rifa n8n: fallo al notificar boletos creados de %s (campaña %s)',
                    partner.display_name, campaign.name, exc_info=True,
                )
