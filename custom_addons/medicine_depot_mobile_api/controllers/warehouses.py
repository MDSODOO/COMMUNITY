# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from ..utils.token_helper import mobile_auth_required


class MobileWarehousesController(http.Controller):

    @http.route('/api/mobile/v1/warehouses', type='http', auth='public', methods=['GET'], csrf=False)
    @mobile_auth_required
    def warehouses(self, user=None, **kw):
        env = request.env
        warehouses = env['stock.warehouse'].sudo().search([])
        return request.make_json_response({
            'results': [{
                'id': w.id,
                'name': w.name,
                'code': w.code,
                'city': w.partner_id.city if w.partner_id else None,
            } for w in warehouses],
        })
