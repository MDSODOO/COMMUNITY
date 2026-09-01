# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from ..utils.token_helper import mobile_auth_required

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


def _serialize_order(order):
    return {
        'id': order.id,
        'name': order.name,
        'state': order.state,
        'date_order': order.date_order.isoformat() if order.date_order else None,
        'amount_total': order.amount_total,
        'lines': [{
            'product_id': line.product_id.product_tmpl_id.id,
            'product_name': line.product_id.display_name,
            'qty': line.product_uom_qty,
            'price_unit': line.price_unit,
            'price_subtotal': line.price_subtotal,
        } for line in order.order_line],
    }


class MobileOrdersController(http.Controller):

    @http.route('/api/mobile/v1/orders', type='http', auth='public', methods=['GET'], csrf=False)
    @mobile_auth_required
    def list_orders(self, user=None, limit=None, offset=None, **kw):
        env = request.env
        try:
            limit = min(int(limit or _DEFAULT_LIMIT), _MAX_LIMIT)
            offset = int(offset or 0)
        except (TypeError, ValueError):
            return request.make_json_response({'error': 'invalid_pagination'}, status=400)

        # state='sale' ya excluye el carrito (siempre 'draft') y cancelados;
        # esta build de Odoo 19 no tiene un estado 'done' separado (ver
        # sale.order._fields['state'].selection) -- lo "cerrado" es un
        # booleano `locked` aparte, no un estado.
        Order = env['sale.order'].sudo()
        domain = [('partner_id', '=', user.partner_id.id), ('state', '=', 'sale')]
        total = Order.search_count(domain)
        orders = Order.search(domain, limit=limit, offset=offset, order='date_order desc')
        return request.make_json_response({
            'total': total,
            'limit': limit,
            'offset': offset,
            'results': [_serialize_order(o) for o in orders],
        })
