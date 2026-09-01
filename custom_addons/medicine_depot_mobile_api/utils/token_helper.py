# -*- coding: utf-8 -*-
import base64
import functools
import hashlib
import hmac
import json
import secrets
import time

from odoo.http import request

_CONFIG_KEY = 'medicine_depot_mobile_api.token_secret'
_ACCESS_TOKEN_TTL = 15 * 60  # 15 minutos, mismo TTL que el patrón de referencia (quifamesa_mobile_api)


def _get_secret(env):
    ICP = env['ir.config_parameter'].sudo()
    secret = ICP.get_param(_CONFIG_KEY)
    if not secret:
        secret = secrets.token_hex(32)
        ICP.set_param(_CONFIG_KEY, secret)
    return secret.encode()


def _b64url_encode(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=')


def _b64url_decode(data):
    return base64.urlsafe_b64decode(data + b'=' * (-len(data) % 4))


def encode_token(env, user_id):
    """Token de sesión firmado con HMAC-SHA256: mismo rol que el JWT de
    quifamesa_mobile_api (payload {uid, iat, exp} + firma), implementado con
    la librería estándar porque PyJWT no está instalado en esta imagen
    (odoo:19.0 stock -- la imagen de Quifamesa es una build propia que ya lo
    incluye). Añadir PyJWT de forma duradera requeriría un Dockerfile propio
    para este servicio; fuera del alcance de este cambio.
    """
    now = int(time.time())
    payload = {'uid': user_id, 'iat': now, 'exp': now + _ACCESS_TOKEN_TTL}
    body = _b64url_encode(json.dumps(payload).encode())
    sig = _b64url_encode(hmac.new(_get_secret(env), body, hashlib.sha256).digest())
    return (body + b'.' + sig).decode(), _ACCESS_TOKEN_TTL


def decode_token(env, token):
    try:
        body, sig = token.encode().split(b'.')
    except ValueError:
        raise ValueError('invalid_token')
    expected_sig = _b64url_encode(hmac.new(_get_secret(env), body, hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected_sig):
        raise ValueError('invalid_token')
    payload = json.loads(_b64url_decode(body))
    if payload['exp'] < int(time.time()):
        raise ValueError('expired')
    return payload


def mobile_auth_required(func):
    """Valida 'Authorization: Bearer <token>' contra el token firmado emitido
    por /auth/login o /auth/refresh, y liga request.env al usuario antes de
    llamar al endpoint."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        env = request.env
        header = request.httprequest.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return request.make_json_response({'error': 'missing_bearer_token'}, status=401)
        token = header[len('Bearer '):].strip()
        try:
            payload = decode_token(env, token)
        except ValueError as exc:
            code = 'token_expired' if str(exc) == 'expired' else 'invalid_token'
            return request.make_json_response({'error': code}, status=401)
        user = env['res.users'].sudo().browse(payload['uid'])
        if not user.exists() or not user.active:
            return request.make_json_response({'error': 'invalid_token'}, status=401)
        request.update_env(user=user.id)
        kwargs['user'] = request.env.user
        return func(self, *args, **kwargs)
    return wrapper
