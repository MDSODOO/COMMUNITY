# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from ..utils.token_helper import mobile_auth_required

# Deliberadamente excluye email/name/vat: identidad y datos fiscales no se
# editan por un endpoint de "perfil básico" sin un flujo de validación aparte.
_EDITABLE_FIELDS = ('phone', 'street', 'street2', 'city', 'zip')


def _serialize_address(partner):
    return {
        'id': partner.id,
        'type': partner.type,
        'name': partner.name,
        'street': partner.street,
        'street2': partner.street2,
        'city': partner.city,
        'state': partner.state_id.name if partner.state_id else None,
        'zip': partner.zip,
        'country': partner.country_id.name if partner.country_id else None,
    }


def _serialize_profile(partner):
    return {
        'id': partner.id,
        'name': partner.name,
        'email': partner.email,
        # res.partner no tiene campo 'mobile' en esta build de Odoo 19 -- se
        # consolidó en 'phone' (solo queda 'phone_mobile_search', un helper
        # de búsqueda, no un campo real que se pueda leer/escribir).
        'phone': partner.phone,
        'vat': partner.vat,
        'l10n_mx_regimen_fiscal': partner.l10n_mx_regimen_fiscal,
        'l10n_mx_uso_cfdi': partner.l10n_mx_uso_cfdi,
        # clasificación real de contactos: category_id (tags), no un campo Studio.
        'tags': partner.category_id.mapped('name'),
        'contact_type': partner.x_studio_contact_type,
        'main_address': _serialize_address(partner),
        'addresses': [
            _serialize_address(child)
            for child in partner.child_ids
            if child.type in ('delivery', 'invoice') and child.active
        ],
    }


class MobileProfileController(http.Controller):

    @http.route('/api/mobile/v1/profile', type='http', auth='public', methods=['GET'], csrf=False)
    @mobile_auth_required
    def get_profile(self, user=None, **kw):
        return request.make_json_response(_serialize_profile(user.partner_id.sudo()))

    @http.route('/api/mobile/v1/profile', type='http', auth='public', methods=['PATCH'], csrf=False)
    @mobile_auth_required
    def update_profile(self, user=None, **kw):
        body = request.get_json_data() or {}
        values = {k: v for k, v in body.items() if k in _EDITABLE_FIELDS}
        if not values:
            return request.make_json_response({'error': 'no_editable_fields'}, status=400)
        user.partner_id.sudo().write(values)
        return request.make_json_response(_serialize_profile(user.partner_id.sudo()))
