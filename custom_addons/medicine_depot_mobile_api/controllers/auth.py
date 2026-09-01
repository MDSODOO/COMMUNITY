# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request

from ..utils.token_helper import encode_token, mobile_auth_required

_API_KEY_SCOPE = 'medicine_depot_mobile'
_API_KEY_NAME = 'Medicine Depot Mobile App'


class MobileAuthController(http.Controller):

    def _issue_session(self, env, user):
        token, expires_in = encode_token(env, user.id)
        existing = env['res.users.apikeys'].sudo().search([
            ('user_id', '=', user.id), ('scope', '=', _API_KEY_SCOPE),
        ], limit=1)
        api_key = None
        if not existing:
            # El valor en claro solo viaja en esta respuesta (Odoo guarda la
            # api_key hasheada). su=True es necesario para generarla sin
            # límite de expiración por grupo del usuario portal.
            api_key = env(user=user.id, su=True)['res.users.apikeys']._generate(
                _API_KEY_SCOPE, _API_KEY_NAME, False,
            )
        is_salesperson = (not user.share) and user.has_group('sales_team.group_sale_salesman')
        is_admin = (not user.share) and user.has_group('base.group_system')
        return {
            'access_token': token,
            'expires_in': expires_in,
            'token_type': 'Bearer',
            'api_key': api_key,
            'user': {
                'id': user.id,
                'name': user.name,
                'login': user.login,
                'is_portal_customer': bool(user.share),
                'is_salesperson': bool(is_salesperson),
                'is_admin': bool(is_admin),
                'partner_id': user.partner_id.id if user.partner_id else None,
            },
        }

    @http.route('/api/mobile/v1/auth/login', type='http', auth='public', methods=['POST'], csrf=False)
    def login(self, **kw):
        env = request.env
        body = request.get_json_data() or {}
        login = body.get('login')
        password = body.get('password')
        if not login or not password:
            return request.make_json_response({'error': 'missing_credentials'}, status=400)
        try:
            auth_info = env['res.users'].sudo().authenticate(
                {'type': 'password', 'login': login, 'password': password}, {'interactive': False},
            )
        except AccessDenied:
            return request.make_json_response({'error': 'invalid_credentials'}, status=401)
        user = env['res.users'].sudo().browse(auth_info['uid'])
        return request.make_json_response(self._issue_session(env, user))

    @http.route('/api/mobile/v1/auth/refresh', type='http', auth='public', methods=['POST'], csrf=False)
    def refresh(self, **kw):
        env = request.env
        body = request.get_json_data() or {}
        api_key = body.get('api_key')
        if not api_key:
            return request.make_json_response({'error': 'missing_api_key'}, status=400)
        uid = env['res.users.apikeys'].sudo()._check_credentials(scope=_API_KEY_SCOPE, key=api_key)
        if not uid:
            return request.make_json_response({'error': 'invalid_api_key'}, status=401)
        user = env['res.users'].sudo().browse(uid)
        token, expires_in = encode_token(env, user.id)
        return request.make_json_response({
            'access_token': token, 'expires_in': expires_in, 'token_type': 'Bearer',
        })

    @http.route('/api/mobile/v1/auth/me', type='http', auth='public', methods=['GET'], csrf=False)
    @mobile_auth_required
    def me(self, user=None, **kw):
        return request.make_json_response(self._issue_session(request.env, user))
