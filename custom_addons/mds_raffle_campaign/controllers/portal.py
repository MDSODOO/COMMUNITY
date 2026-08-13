import json

from odoo import http
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
