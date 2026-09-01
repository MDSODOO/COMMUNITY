# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from ..utils.token_helper import mobile_auth_required

_EDITABLE_FIELDS = ('name', 'street', 'street2', 'city', 'zip', 'state_id', 'country_id', 'phone')


def _serialize_address(partner):
    return {
        'id': partner.id,
        'type': partner.type,
        'name': partner.name,
        'street': partner.street,
        'street2': partner.street2,
        'city': partner.city,
        'state_id': partner.state_id.id if partner.state_id else None,
        'state': partner.state_id.name if partner.state_id else None,
        'zip': partner.zip,
        'country_id': partner.country_id.id if partner.country_id else None,
        'country': partner.country_id.name if partner.country_id else None,
        'phone': partner.phone,
    }


def _get_own_address(env, user, address_id):
    """Solo direcciones type='delivery' cuyo parent_id sea el partner
    autenticado -- nunca confiar en address_id solo, o cualquier usuario
    podria leer/editar direcciones ajenas adivinando ids."""
    address = env['res.partner'].sudo().browse(address_id)
    if (not address.exists() or address.type != 'delivery'
            or address.parent_id.id != user.partner_id.id or not address.active):
        return env['res.partner']
    return address


def _clean_values(body):
    values = {k: v for k, v in body.items() if k in _EDITABLE_FIELDS}
    for int_field in ('state_id', 'country_id'):
        if int_field in values and values[int_field] is not None:
            try:
                values[int_field] = int(values[int_field])
            except (TypeError, ValueError):
                return None
    return values


class MobileAddressesController(http.Controller):

    @http.route('/api/mobile/v1/addresses', type='http', auth='public', methods=['GET'], csrf=False)
    @mobile_auth_required
    def list_addresses(self, user=None, **kw):
        addresses = request.env['res.partner'].sudo().search([
            ('parent_id', '=', user.partner_id.id),
            ('type', '=', 'delivery'),
            ('active', '=', True),
        ])
        return request.make_json_response({'results': [_serialize_address(a) for a in addresses]})

    @http.route('/api/mobile/v1/addresses', type='http', auth='public', methods=['POST'], csrf=False)
    @mobile_auth_required
    def create_address(self, user=None, **kw):
        body = request.get_json_data() or {}
        if not (body.get('name') or '').strip():
            return request.make_json_response({'error': 'missing_name'}, status=400)
        values = _clean_values(body)
        if values is None:
            return request.make_json_response({'error': 'invalid_state_or_country'}, status=400)
        values.update({'parent_id': user.partner_id.id, 'type': 'delivery'})
        address = request.env['res.partner'].sudo().create(values)
        return request.make_json_response(_serialize_address(address), status=201)

    @http.route('/api/mobile/v1/addresses/<int:address_id>', type='http', auth='public', methods=['PATCH'], csrf=False)
    @mobile_auth_required
    def update_address(self, address_id, user=None, **kw):
        address = _get_own_address(request.env, user, address_id)
        if not address:
            return request.make_json_response({'error': 'address_not_found'}, status=404)
        values = _clean_values(request.get_json_data() or {})
        if values is None:
            return request.make_json_response({'error': 'invalid_state_or_country'}, status=400)
        if not values:
            return request.make_json_response({'error': 'no_editable_fields'}, status=400)
        address.write(values)
        return request.make_json_response(_serialize_address(address))

    @http.route('/api/mobile/v1/addresses/<int:address_id>', type='http', auth='public', methods=['DELETE'], csrf=False)
    @mobile_auth_required
    def delete_address(self, address_id, user=None, **kw):
        # Soft-delete (archivar): unlink() sobre res.partner arriesga romper
        # FKs si la direccion ya se uso en algun pedido. active=False es
        # reversible y es la convencion estandar de Odoo para "borrar" partners.
        address = _get_own_address(request.env, user, address_id)
        if not address:
            return request.make_json_response({'error': 'address_not_found'}, status=404)
        address.write({'active': False})
        return request.make_json_response({'status': 'ok'})
