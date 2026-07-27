# -*- coding: utf-8 -*-
"""
Traduce una pregunta de inventario en lenguaje natural a una consulta real
de stock.quant, y arma la respuesta final en Python -- el modelo de IA
solo identifica a que producto se refiere el usuario, nunca redacta ni
inventa la cantidad "A la mano" (On Hand). Ver docs/AI_MODEL_ODOO_CONFIG.md
§4/§5.1/§6.3 para la justificacion de este diseno.
"""
import logging

from . import ollama_client, prompt_templates

_logger = logging.getLogger(__name__)

MODEL = "qwen2.5-coder:7b"


def resolve_inventory_query(env, question):
    """
    Devuelve un dict:
      status: 'ok' | 'clarify' | 'not_found' | 'error'
      message: texto listo para mostrar al usuario (siempre usa 'A la mano')
      product_id: int o None
      on_hand: float o None
      raw_model_output: dict o None (para auditoria, ver ai_query_log.py)
    """
    prompt = prompt_templates.INVENTORY_QUERY_PROMPT.format(question=question)

    try:
        parsed = ollama_client.generate_structured(
            model=MODEL,
            prompt=prompt,
            json_schema=prompt_templates.INVENTORY_QUERY_SCHEMA,
        )
    except ollama_client.OllamaError as exc:
        return {
            "status": "error",
            "message": "No se pudo procesar la pregunta en este momento. Intenta de nuevo en un momento.",
            "product_id": None,
            "on_hand": None,
            "raw_model_output": None,
            "error": str(exc),
        }

    if not isinstance(parsed, dict) or "producto_mencionado" not in parsed:
        _logger.warning("inventory_nl_resolver: forma de respuesta inesperada: %r", parsed)
        return {
            "status": "error",
            "message": "No se pudo interpretar la pregunta. Intenta reformularla.",
            "product_id": None,
            "on_hand": None,
            "raw_model_output": parsed,
        }

    mentioned = parsed.get("producto_mencionado")
    if parsed.get("aclaracion_necesaria") or not mentioned:
        return {
            "status": "clarify",
            "message": (
                "No identifique un producto especifico en tu pregunta. "
                "¿Podrias indicar el nombre o el codigo de barras del producto?"
            ),
            "product_id": None,
            "on_hand": None,
            "raw_model_output": parsed,
        }

    Product = env["product.product"].sudo()
    domain = [
        "|", "|",
        ("name", "ilike", mentioned),
        ("barcode", "=", mentioned),
        ("default_code", "=", mentioned),
    ]
    products = Product.search(domain, limit=6)

    if not products:
        return {
            "status": "not_found",
            "message": 'No encontre ningun producto que coincida con "{}".'.format(mentioned),
            "product_id": None,
            "on_hand": None,
            "raw_model_output": parsed,
        }

    if len(products) > 1:
        options = "; ".join(products.mapped("display_name"))
        return {
            "status": "clarify",
            "message": "Encontre varios productos que podrian coincidir: {}. ¿Cual te interesa?".format(options),
            "product_id": None,
            "on_hand": None,
            "raw_model_output": parsed,
        }

    product = products
    quants = env["stock.quant"].sudo().search([
        ("product_id", "=", product.id),
        ("location_id.usage", "=", "internal"),
    ])
    on_hand = sum(quants.mapped("quantity"))

    return {
        "status": "ok",
        "message": 'A la mano de "{}": {:g} {}.'.format(
            product.display_name, on_hand, product.uom_id.name
        ),
        "product_id": product.id,
        "on_hand": on_hand,
        "raw_model_output": parsed,
    }
