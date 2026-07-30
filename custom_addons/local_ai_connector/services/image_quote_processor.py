# -*- coding: utf-8 -*-
"""
Procesa UNA solicitud de cotizacion por imagen pendiente: redimensiona cada
foto, extrae renglones via qwen2.5vl:7b (prompt/schema v3), y corre el
matching de producto. Pensado para ser llamado desde un cron (ver
data/image_quote_cron.xml) -- Odoo serializa las ejecuciones de una misma
entrada de cron, que es lo que realmente evita procesar 2 solicitudes en
paralelo (ver nota en ollama_client.py).
"""
import base64
import io
import logging

from PIL import Image, UnidentifiedImageError

from . import ollama_client, prompt_templates
from .image_quote_matcher import match_product

_logger = logging.getLogger(__name__)

# Mismo valor usado y verificado en scripts/test_vision_extraction.py --
# imagenes reales sin redimensionar tardaron >10 min (se tuvo que cancelar
# la corrida), con este limite bajaron a 93-242s.
MAX_DIMENSION = 1024


def _resize_image(binary_data):
    """Redimensiona a MAX_DIMENSION por lado mayor, devuelve base64 JPEG."""
    try:
        img = Image.open(io.BytesIO(binary_data))
    except UnidentifiedImageError as exc:
        raise ValueError("El archivo no es una imagen válida.") from exc

    img = img.convert("RGB")
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def process_next_pending_request(env):
    """Procesa la solicitud 'pending' mas antigua, si existe. No lanza
    excepciones hacia afuera -- cualquier error deja la solicitud en estado
    'error' con el detalle, para que el cron siga corriendo sin interrumpirse."""
    Request = env["local.ai.image.quote.request"].sudo()
    request = Request.search([("state", "=", "pending")], order="create_date asc", limit=1)
    if not request:
        return False

    request.write({"state": "processing"})
    env.cr.commit()  # visible de inmediato para cualquier UI/consulta mientras procesa

    try:
        _process_request(env, request)
    except ollama_client.OllamaBusyError:
        _logger.warning(
            "image_quote_processor: Ollama busy, re-queuing request %s", request.name
        )
        request.write({"state": "pending"})
        env.cr.commit()
    except Exception as exc:  # noqa: BLE001 -- este es el limite de aislamiento del cron
        _logger.exception("image_quote_processor: fallo procesando %s", request.name)
        request.write({"state": "error", "error_message": str(exc)})
        env.cr.commit()

    return True


def _process_request(env, request):
    Line = env["local.ai.image.quote.line"].sudo()
    any_line_created = False

    for image in request.image_ids:
        if image.extraction_status == 'done':
            continue

        try:
            img_b64 = _resize_image(base64.b64decode(image.image))
            parsed = ollama_client.generate_structured(
                model=prompt_templates.IMAGE_QUOTE_MODEL,
                prompt=prompt_templates.IMAGE_QUOTE_PROMPT,
                json_schema=prompt_templates.IMAGE_QUOTE_SCHEMA,
                images=[img_b64],
                timeout=ollama_client.VISION_TIMEOUT,
                num_ctx=8192,
                priority='low',
                cr=env.cr,
            )
        except ollama_client.OllamaBusyError:
            raise
        except (ollama_client.OllamaError, ValueError) as exc:
            image.write({"extraction_status": "error", "error_message": str(exc)})
            continue

        if not isinstance(parsed, list):
            image.write({
                "extraction_status": "error",
                "error_message": "El modelo no devolvió una lista (schema inesperado).",
            })
            continue

        image.write({
            "extraction_status": "done",
            "extraction_raw": str(parsed),
        })

        for item in parsed:
            if not isinstance(item, dict):
                continue
            text_detected = (item.get("texto_detectado") or "").strip()
            if not text_detected:
                continue
            quantity = item.get("cantidad_detectada")

            match = match_product(env, text_detected)
            Line.create({
                "request_id": request.id,
                "source_image_id": image.id,
                "text_detected": text_detected,
                "quantity_detected": quantity or 0.0,
                "product_id": match["product"].id if match["product"] else False,
                "match_confidence": match["confidence"],
                "match_method": match["method"],
                "match_status": match["status"],
            })
            any_line_created = True

    if any_line_created:
        request.write({"state": "ready_for_review"})
    else:
        request.write({
            "state": "error",
            "error_message": "No se pudo extraer ningún renglón de ninguna de las imágenes.",
        })
