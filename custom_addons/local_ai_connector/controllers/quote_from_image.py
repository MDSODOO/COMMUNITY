# -*- coding: utf-8 -*-
import base64
import logging
from datetime import timedelta

from odoo import fields, http
from odoo.http import request
from .csrf_utils import validate_origin

_logger = logging.getLogger(__name__)

# Limite mas estricto que /afiliacion (5/15min): cada solicitud aqui cuesta
# 90-240s de CPU + hasta 6.7GB de RAM (modelo de vision), no solo un
# registro en Postgres -- ver docs/AI_MODEL_ODOO_CONFIG.md §9.1.
_RATE_LIMIT_WINDOW_SECONDS = 60 * 60
_RATE_LIMIT_MAX_ATTEMPTS = 3

_MAX_FILE_SIZE = 8 * 1024 * 1024  # 8 MB por foto
_ALLOWED_MIMETYPES = {'image/jpeg', 'image/png'}
_MAX_IMAGES_PER_REQUEST = 5


class LocalAiQuoteFromImageController(http.Controller):

    def _get_request_ip(self):
        return request.httprequest.remote_addr or 'unknown'

    def _is_rate_limited(self, ip):
        Attempt = request.env['local.ai.image.quote.attempt'].sudo()
        window_start = fields.Datetime.now() - timedelta(seconds=_RATE_LIMIT_WINDOW_SECONDS)
        attempt_count = Attempt.search_count([
            ('ip_address', '=', ip),
            ('create_date', '>=', window_start),
        ])
        if attempt_count >= _RATE_LIMIT_MAX_ATTEMPTS:
            return True
        Attempt.create({'ip_address': ip})
        return False

    @http.route(
        '/ai/quote_from_image',
        type='http', auth='public', website=True,
        methods=['POST'],
        csrf=False,  # multipart/form-data sin sesion; protegido via validate_origin()
    )
    def quote_from_image(self, **post):
        """Recibe 1+ fotos de una cotizacion escrita/impresa a mano y
        encola su procesamiento -- NUNCA procesa en esta misma request
        (una imagen real tarda 90-240s, ver docs/AI_MODEL_ODOO_CONFIG.md §9.2).
        Un cron la recoge despues (services/image_quote_processor.py) y un
        humano de staff revisa cada renglon antes de crear cualquier
        cotizacion real -- ver action_create_quotation en
        models/image_quote_request.py.
        """
        csrf_error = validate_origin()
        if csrf_error:
            return csrf_error

        ip = self._get_request_ip()
        if self._is_rate_limited(ip):
            _logger.warning(
                'quote_from_image: rate limit alcanzado para IP %s (%s intentos / %s min)',
                ip, _RATE_LIMIT_MAX_ATTEMPTS, _RATE_LIMIT_WINDOW_SECONDS // 60,
            )
            return request.make_json_response({
                'success': False,
                'message': 'Demasiados intentos. Por favor espera antes de volver a intentar.',
            }, status=429)

        customer_name = (post.get('customer_name') or '').strip()
        customer_email = (post.get('customer_email') or '').strip()
        customer_phone = (post.get('customer_phone') or '').strip()

        if not customer_name or not customer_email:
            return request.make_json_response({
                'success': False,
                'message': 'Nombre y correo son obligatorios.',
            }, status=400)

        files = request.httprequest.files.getlist('images')
        if not files:
            return request.make_json_response({
                'success': False,
                'message': 'Sube al menos una foto.',
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
                _logger.warning('quote_from_image: mimetype no permitido (%s)', mimetype)
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
            'ip_address': ip,
            'origin_channel': 'public_web',
            'image_ids': image_vals,
        })

        return request.make_json_response({
            'success': True,
            'message': 'Recibido. Un miembro de nuestro equipo revisará tu solicitud y te contactaremos con la cotización.',
            'reference': quote_request.name,
        })
