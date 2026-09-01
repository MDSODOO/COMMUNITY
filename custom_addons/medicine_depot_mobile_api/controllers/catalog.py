# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from ..utils.token_helper import mobile_auth_required

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


class MobileCatalogController(http.Controller):

    @http.route('/api/mobile/v1/catalog/products', type='http', auth='public', methods=['GET'], csrf=False)
    @mobile_auth_required
    def products(self, user=None, limit=None, offset=None, **kw):
        env = request.env
        try:
            limit = min(int(limit or _DEFAULT_LIMIT), _MAX_LIMIT)
            offset = int(offset or 0)
        except (TypeError, ValueError):
            return request.make_json_response({'error': 'invalid_pagination'}, status=400)

        Product = env['product.template'].sudo()
        domain = [('sale_ok', '=', True), ('active', '=', True)]
        total = Product.search_count(domain)
        products = Product.search(domain, limit=limit, offset=offset, order='name')
        return request.make_json_response({
            'total': total,
            'limit': limit,
            'offset': offset,
            'results': [{
                'id': p.id,
                'name': p.name,
                'barcode': p.barcode,
                'list_price': p.list_price,
                'qty_available': p.qty_available,
                'registro_sanitario': p.l10n_mx_registro_sanitario,
                'requiere_receta': p.l10n_mx_requiere_receta,
                'forma_farmaceutica': p.l10n_mx_forma_farmaceutica,
                'concentracion': p.l10n_mx_concentracion,
            } for p in products],
        })
