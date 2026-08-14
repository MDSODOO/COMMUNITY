import json

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request


class RaffleCustomerPortal(http.Controller):

    @http.route(['/my/rifa'], type='http', auth='user', sitemap=False, csrf=False)
    def my_raffle_status(self, **kwargs):
        """Estado de la rifa del cliente logueado, en JSON plano (no
        JSON-RPC) para que un frontend Next.js lo consuma con un fetch()
        normal. Shape de respuesta:

        {
          "partner_id": int,
          "campaigns": [
            {
              "campaign_id": int,
              "campaign_name": str,
              "campaign_code": str,
              "state": "draft" | "active" | "closed" | "drawn",
              "ticket_count": int,
              "physical_count": int,
              "online_count": int,
              "folios": [str, ...],
              "bonuses": {"sponsor_line": bool, "sponsor_catalog": bool}
            }, ...
          ]
        }
        """
        partner = request.env.user.partner_id
        summaries = request.env['raffle.ticket.summary'].sudo().search([
            ('partner_id', '=', partner.id),
        ])
        data = {
            'partner_id': partner.id,
            'campaigns': [{
                'campaign_id': summary.campaign_id.id,
                'campaign_name': summary.campaign_id.name,
                'campaign_code': summary.campaign_id.code,
                'state': summary.campaign_id.state,
                'ticket_count': summary.ticket_count,
                'physical_count': summary.physical_count,
                'online_count': summary.online_count,
                'folios': [
                    ref.strip() for ref in (summary.legacy_refs or '').split(',') if ref.strip()
                ],
                'bonuses': {
                    'sponsor_line': summary.has_sponsor_line,
                    'sponsor_catalog': summary.has_sponsor_catalog,
                },
            } for summary in summaries],
        }
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')],
        )


class RafflePortal(CustomerPortal):

    _raffle_items_per_page = 20

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'raffle_ticket_count' in counters:
            partner = request.env.user.partner_id
            Ticket = request.env['raffle.ticket'].sudo()
            values['raffle_ticket_count'] = Ticket.search_count([
                ('partner_id', '=', partner.id),
                ('state', '=', 'valid'),
            ])
        return values

    @http.route(['/my/raffles', '/my/raffles/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_raffles(self, page=1, **kwargs):
        partner = request.env.user.partner_id
        Ticket = request.env['raffle.ticket'].sudo()
        domain = [('partner_id', '=', partner.id), ('state', '=', 'valid')]

        pager_values = portal_pager(
            url='/my/raffles',
            total=Ticket.search_count(domain),
            page=page,
            step=self._raffle_items_per_page,
        )
        tickets = Ticket.search(
            domain, order='campaign_id, id desc',
            limit=self._raffle_items_per_page, offset=pager_values['offset'],
        )
        summaries = request.env['raffle.ticket.summary'].sudo().search([
            ('partner_id', '=', partner.id),
        ])

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'raffle',
            'tickets': tickets,
            'summaries': summaries,
            'pager': pager_values,
            'default_url': '/my/raffles',
        })
        return request.render('mds_raffle_campaign.portal_my_raffles', values)
