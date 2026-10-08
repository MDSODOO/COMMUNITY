import base64
import logging
from datetime import timedelta

from odoo import fields, http
from odoo.http import request

from ..services import ollama_client
from ..services.vision_product_identifier import identify_product_from_photo

_logger = logging.getLogger(__name__)

_RATE_LIMIT_WINDOW_SECONDS = 60 * 60
_RATE_LIMIT_MAX_ATTEMPTS = 20

_MAX_FILE_SIZE = 8 * 1024 * 1024
_ALLOWED_MIMETYPES = {"image/jpeg", "image/png"}


class LocalAiVisionFromPhotoController(http.Controller):

    def _is_rate_limited(self, user_id):
        Attempt = request.env["local.ai.image.quote.attempt"].sudo()
        window_start = fields.Datetime.now() - timedelta(
            seconds=_RATE_LIMIT_WINDOW_SECONDS
        )
        attempt_count = Attempt.search_count([
            ("user_id", "=", user_id),
            ("create_date", ">=", window_start),
        ])
        if attempt_count >= _RATE_LIMIT_MAX_ATTEMPTS:
            return True
        Attempt.create({"user_id": user_id})
        return False

    @http.route(
        "/ai/identify_product_from_photo",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=True,
    )
    def identify_product_from_photo(self, **post):
        user = request.env.user

        if self._is_rate_limited(user.id):
            _logger.warning(
                "identify_product_from_photo: rate limit alcanzado para usuario %s",
                user.login,
            )
            return request.make_json_response(
                {
                    "success": False,
                    "error": "rate_limited",
                    "message": "Demasiadas solicitudes seguidas. Espera unos minutos "
                    "antes de volver a intentar.",
                },
                status=429,
            )

        file_obj = request.httprequest.files.get("image")
        if not file_obj:
            return request.make_json_response(
                {
                    "success": False,
                    "error": "no_file",
                    "message": "Sube una foto del producto.",
                },
                status=400,
            )

        content = file_obj.read()
        if len(content) > _MAX_FILE_SIZE:
            return request.make_json_response(
                {
                    "success": False,
                    "error": "file_too_large",
                    "message": "La foto debe pesar menos de %s MB."
                    % (_MAX_FILE_SIZE // (1024 * 1024)),
                },
                status=400,
            )

        mimetype = file_obj.content_type or "application/octet-stream"
        if mimetype not in _ALLOWED_MIMETYPES:
            _logger.warning(
                "identify_product_from_photo: mimetype no permitido (%s)", mimetype
            )
            return request.make_json_response(
                {
                    "success": False,
                    "error": "invalid_format",
                    "message": "Solo se aceptan fotos JPEG o PNG.",
                },
                status=400,
            )

        try:
            result = identify_product_from_photo(
                request.env, content, image_filename=file_obj.filename
            )
            return request.make_json_response(result)
        except ollama_client.OllamaBusyError:
            return request.make_json_response(
                {
                    "success": False,
                    "error": "busy",
                    "message": "El modelo de IA esta procesando otra imagen. "
                    "Intenta de nuevo en un momento.",
                },
                status=503,
            )
        except ollama_client.OllamaError as exc:
            _logger.warning(
                "identify_product_from_photo: error de modelo para usuario %s: %s",
                user.login,
                exc,
            )
            return request.make_json_response(
                {
                    "success": False,
                    "error": "ai_unavailable",
                    "message": "El servicio de IA local no esta disponible en este "
                    "momento. Contacta al administrador del sistema.",
                },
                status=503,
            )
        except Exception as exc:
            _logger.exception(
                "identify_product_from_photo: error inesperado para usuario %s",
                user.login,
            )
            return request.make_json_response(
                {
                    "success": False,
                    "error": "internal_error",
                    "message": "Ocurrio un error inesperado. Intenta de nuevo o "
                    "contacta al administrador.",
                },
                status=500,
            )
