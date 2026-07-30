import base64
import io
import logging

from PIL import Image, UnidentifiedImageError

from odoo import _

from . import ollama_client, prompt_templates

_logger = logging.getLogger(__name__)

VISION_TIMEOUT = 300
MAX_DIMENSION = 1024
IDENTIFY_CONFIDENCE_THRESHOLD_MEDIUM = 0.5
IDENTIFY_CONFIDENCE_THRESHOLD_HIGH = 0.8


class ProductIdentificationError(Exception):
    """Error controlado durante la identificacion de producto desde foto."""


def _resize_image(binary_data):
    try:
        img = Image.open(io.BytesIO(binary_data))
    except UnidentifiedImageError as exc:
        raise ValueError("El archivo no es una imagen valida.") from exc
    img = img.convert("RGB")
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def _search_product(env, nombre_comercial, principio_activo):
    Product = env["product.product"].sudo()
    domain = [("sale_ok", "=", True)]
    if nombre_comercial:
        domain.append(("name", "ilike", nombre_comercial[:60]))
    else:
        domain.append(("name", "ilike", principio_activo[:60])) if principio_activo else None
    return Product.search(domain, limit=5)


def _search_by_active_ingredient(env, principio_activo):
    Product = env["product.product"].sudo()
    product = Product.search([
        "|",
        ("product_tmpl_id.x_studio_active_ingredient", "ilike", principio_activo[:60]),
        ("product_tmpl_id.description_sale", "ilike", principio_activo[:60]),
        ("sale_ok", "=", True),
    ], limit=5)
    if not product:
        product = Product.search([
            ("product_tmpl_id.description", "ilike", principio_activo[:60]),
            ("sale_ok", "=", True),
        ], limit=5)
    return product


def _compute_on_hand(env, product):
    quants = env["stock.quant"].sudo().search([
        ("product_id", "=", product.id),
        ("location_id.usage", "=", "internal"),
    ])
    return sum(quants.mapped("quantity"))


def identify_product_from_photo(env, image_data, image_filename=""):
    """Identifica un producto desde una foto.

    Args:
        env: entorno Odoo
        image_data: bytes de la imagen
        image_filename: nombre del archivo (para log)

    Returns:
        dict con:
            success: bool
            product: {id, name, A_la_mano: float} o None
            identification: {nombre_comercial, principio_activo, presentacion, cantidad_solicitada}
            confidence: float
            match_status: 'auto' | 'review' | 'not_found' | 'low_confidence'
            message: str

    Raises:
        ollama_client.OllamaBusyError: si el advisory lock esta ocupado
        ollama_client.OllamaError: si el modelo falla
    """
    img_b64 = _resize_image(image_data)

    parsed = ollama_client.generate_structured(
        model=prompt_templates.VISION_PRODUCT_IDENTIFIER_MODEL,
        prompt=prompt_templates.VISION_PRODUCT_IDENTIFIER_PROMPT,
        json_schema=prompt_templates.VISION_PRODUCT_IDENTIFIER_SCHEMA,
        images=[img_b64],
        timeout=VISION_TIMEOUT,
        num_ctx=8192,
        priority="low",
        cr=env.cr,
    )

    if not isinstance(parsed, dict):
        raise ProductIdentificationError(
            "El modelo devolvio una respuesta con formato inesperado."
        )

    nombre_comercial = parsed.get("nombre_comercial")
    principio_activo = parsed.get("principio_activo")
    presentacion = parsed.get("presentacion")
    cantidad_solicitada = parsed.get("cantidad_solicitada")
    confidence = parsed.get("confianza", 0.0)

    identification = {
        "nombre_comercial": nombre_comercial,
        "principio_activo": principio_activo,
        "presentacion": presentacion,
        "cantidad_solicitada": cantidad_solicitada,
    }

    product = None
    match_status = "not_found"
    on_hand = 0.0

    if confidence >= IDENTIFY_CONFIDENCE_THRESHOLD_MEDIUM and (nombre_comercial or principio_activo):
        products = _search_product(env, nombre_comercial, principio_activo)

        if not products and principio_activo:
            products = _search_by_active_ingredient(env, principio_activo)

        if products:
            if len(products) == 1 or confidence >= IDENTIFY_CONFIDENCE_THRESHOLD_HIGH:
                product = products[0]
                on_hand = _compute_on_hand(env, product)
                match_status = "auto" if confidence >= IDENTIFY_CONFIDENCE_THRESHOLD_HIGH else "review"
            else:
                product = products[0]
                on_hand = _compute_on_hand(env, product)
                match_status = "review"
        else:
            match_status = "not_found"
    else:
        match_status = "low_confidence"

    IdentificationLog = env["local.ai.vision.identification"].sudo()
    log_vals = {
        "image_filename": image_filename or "foto_desde_camara",
        "raw_model_output": str(parsed),
        "product_id": product.id if product else False,
        "confidence": confidence,
        "nombre_comercial": nombre_comercial or "",
        "principio_activo": principio_activo or "",
        "presentacion": presentacion or "",
        "on_hand": on_hand,
        "success": product is not None,
    }
    if product is None:
        log_vals["error_message"] = _("No se encontro producto para: %s") % (
            nombre_comercial or principio_activo or "desconocido"
        )
    IdentificationLog.create(log_vals)

    result = {
        "success": product is not None,
        "product": {
            "id": product.id,
            "name": product.display_name,
            "A_la_mano": on_hand,
        } if product else None,
        "identification": identification,
        "confidence": confidence,
        "match_status": match_status,
        "message": _('Se identifico "%s" con confianza %.0f%%. A la mano: %g %s.') % (
            product.display_name, confidence * 100, on_hand, product.uom_id.name
        ) if product else _("No se pudo identificar el producto en la imagen con suficiente confianza."),
    }
    return result
