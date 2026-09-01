# -*- coding: utf-8 -*-
import logging

import requests

from odoo import http
from odoo.http import request

from ..utils.token_helper import mobile_auth_required

_logger = logging.getLogger(__name__)

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'


def send_expo_push(push_tokens, title, body, data=None):
    """Envía notificaciones push vía la API de Expo. Reutilizable -- todavía
    NO se llama desde ningún trigger de negocio (eso es otra iteración);
    por ahora solo existe la función, lista para usarse.

    push_tokens: lista de strings tipo 'ExponentPushToken[...]'.
    Devuelve el JSON de respuesta de Expo (dict) o None si no había tokens
    o hubo un error de red -- nunca lanza, para que una falla de push no
    tumbe el flujo de negocio que la dispare a futuro (ej. confirmar pedido).
    """
    if not push_tokens:
        return None
    messages = [{'to': token, 'title': title, 'body': body, 'data': data or {}} for token in push_tokens]
    try:
        response = requests.post(
            EXPO_PUSH_URL, json=messages,
            headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
            timeout=10,
        )
        return response.json()
    except requests.RequestException:
        _logger.warning('medicine_depot_mobile_api: fallo de red enviando push a Expo', exc_info=True)
        return None


class MobilePushController(http.Controller):

    @http.route('/api/mobile/v1/push/register', type='http', auth='public', methods=['POST'], csrf=False)
    @mobile_auth_required
    def register(self, user=None, **kw):
        env = request.env
        body = request.get_json_data() or {}
        push_token = (body.get('push_token') or '').strip()
        platform = body.get('platform')
        if not push_token or platform not in ('ios', 'android'):
            return request.make_json_response({'error': 'invalid_payload'}, status=400)

        # Upsert por push_token (no por user_id): mismo criterio que
        # quifamesa_mobile_api -- un token pertenece a la instalación de app
        # que esté logueada ahora mismo en ese dispositivo, así que si ya
        # existía bajo otro usuario (dispositivo compartido / cambio de
        # cuenta) se reasigna al usuario actual en vez de duplicar.
        Device = env['medicine.depot.mobile.device'].sudo()
        device = Device.search([('push_token', '=', push_token)], limit=1)
        vals = {
            'user_id': user.id,
            'push_token': push_token,
            'platform': platform,
            'device_name': (body.get('device_name') or '').strip(),
            'active': True,
        }
        if device:
            device.write(vals)
        else:
            device = Device.create(vals)
        return request.make_json_response({'status': 'ok', 'device_id': device.id})

    @http.route('/api/mobile/v1/push/register', type='http', auth='public', methods=['DELETE'], csrf=False)
    @mobile_auth_required
    def deregister(self, user=None, **kw):
        body = request.get_json_data() or {}
        push_token = (body.get('push_token') or '').strip()
        if not push_token:
            return request.make_json_response({'error': 'missing_push_token'}, status=400)
        # Alcance a user_id=user.id ademas de push_token: un usuario no
        # puede desactivar el dispositivo de otro adivinando/reusando un token.
        device = request.env['medicine.depot.mobile.device'].sudo().search([
            ('push_token', '=', push_token), ('user_id', '=', user.id),
        ], limit=1)
        if not device:
            return request.make_json_response({'error': 'device_not_found'}, status=404)
        device.write({'active': False})
        return request.make_json_response({'status': 'ok'})
