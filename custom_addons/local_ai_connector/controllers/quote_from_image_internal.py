# -*- coding: utf-8 -*-
import base64
import logging
from datetime import timedelta

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

# La mayoria de las cotizaciones llegan por WhatsApp (cuentas normales, sin
# API oficial) a un empleado, no por el formulario publico -- ver
# docs/AI_MODEL_ODOO_CONFIG.md §9.3. Este endpoint deja que ese empleado
# arrastre la foto directo a Odoo (dialogo abierto desde el Command
# Palette / systray) en vez de forzarlo a pasar por /ai/quote_from_image
# (pensado para que el cliente final suba su propia foto).
#
# Limite mas generoso que el publico (3/hora) porque es staff autenticado
# y de confianza, pero sigue habiendo un limite: cada solicitud cuesta
# 90-240s de CPU + hasta 6.7GB de RAM (modelo de vision, ver
# image_quote_processor.py), asi que un arrastre accidental de muchas
# fotos de golpe si debe frenarse. Contado por user_id, no por IP: varios
# empleados comparten la IP de oficina.
_RATE_LIMIT_WINDOW_SECONDS = 60 * 60
_RATE_LIMIT_MAX_ATTEMPTS = 10

_MAX_FILE_SIZE = 8 * 1024 * 1024  # 8 MB por foto, igual que el endpoint publico
_ALLOWED_MIMETYPES = {'image/jpeg', 'image/png'}
_MAX_IMAGES_PER_REQUEST = 5


class LocalAiQuoteFromImageInternalController(http.Controller):

    def _is_rate_limited(self, user_id):
        Attempt = request.env['local.ai.image.quote.attempt'].sudo()
        window_start = fields.Datetime.now() - timedelta(seconds=_RATE_LIMIT_WINDOW_SECONDS)
        attempt_count = Attempt.search_count([
            ('user_id', '=', user_id),
            ('create_date', '>=', window_start),
        ])
        if attempt_count >= _RATE_LIMIT_MAX_ATTEMPTS:
            return True
        Attempt.create({'user_id': user_id})
        return False

    @http.route(
        '/ai/quote_from_image/staff',
        type='http', auth='user', website=True,
        methods=['POST'],
    )
    def quote_from_image_staff(self, **post):
        """Version interna de /ai/quote_from_image: un empleado arrastra o
        selecciona 1+ fotos recibidas por WhatsApp y las encola -- mismo
        pipeline de despues (cron -> extraccion -> matching -> revision)
        que la via publica, ver models/image_quote_request.py.
        """
        user = request.env.user
        if self._is_rate_limited(user.id):
            _logger.warning(
                'quote_from_image_staff: rate limit alcanzado para usuario %s (%s intentos / %s min)',
                user.login, _RATE_LIMIT_MAX_ATTEMPTS, _RATE_LIMIT_WINDOW_SECONDS // 60,
            )
            return request.make_json_response({
                'success': False,
                'message': 'Demasiadas solicitudes seguidas. Espera unos minutos antes de volver a intentar.',
            }, status=429)

        customer_name = (post.get('customer_name') or '').strip()
        customer_email = (post.get('customer_email') or '').strip()
        customer_phone = (post.get('customer_phone') or '').strip()

        if not customer_name:
            return request.make_json_response({
                'success': False,
                'message': 'El nombre del cliente es obligatorio.',
            }, status=400)
        if not customer_email and not customer_phone:
            return request.make_json_response({
                'success': False,
                'message': 'Captura al menos el teléfono o el correo del cliente.',
            }, status=400)

        files = request.httprequest.files.getlist('images')
        if not files:
            return request.make_json_response({
                'success': False,
                'message': 'Adjunta al menos una foto.',
            }, status=400)
        if len(files) > _MAX_IMAGES_PER_REQUEST:
            return request.make_json_response({
                'success': False,
                'message': 'Máximo %s fotos por solicitud.' % _MAX_IMAGES_PER_REQUEST,
            }, status=400)

        image_vals = []
        for file_obj in files:
            content = file_obj.read()
            if len(content) > _MAX_FILE_SIZE:
                return request.make_json_response({
                    'success': False,
                    'message': 'Cada foto debe pesar menos de %s MB.' % (_MAX_FILE_SIZE // (1024 * 1024)),
                }, status=400)
            mimetype = file_obj.content_type or 'application/octet-stream'
            if mimetype not in _ALLOWED_MIMETYPES:
                _logger.warning('quote_from_image_staff: mimetype no permitido (%s)', mimetype)
                return request.make_json_response({
                    'success': False,
                    'message': 'Solo se aceptan fotos JPEG o PNG.',
                }, status=400)
            image_vals.append((0, 0, {
                'image': base64.b64encode(content),
                'image_filename': file_obj.filename,
            }))

        quote_request = request.env['local.ai.image.quote.request'].sudo().create({
            'customer_name': customer_name,
            'customer_email': customer_email,
            'customer_phone': customer_phone,
            'ip_address': request.httprequest.remote_addr,
            'origin_channel': 'internal_staff',
            'image_ids': image_vals,
        })

        return request.make_json_response({
            'success': True,
            'message': 'Solicitud creada. Se procesará en unos minutos.',
            'reference': quote_request.name,
        })
