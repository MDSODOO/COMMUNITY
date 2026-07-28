# -*- coding: utf-8 -*-
"""
Cliente HTTP minimo hacia Ollama, corriendo solo en 127.0.0.1:11434.

Regla de seguridad (docs/AI_MODEL_ODOO_CONFIG.md §2.3, §6.2): Ollama nunca
debe exponerse fuera de localhost -- Odoo (este modulo) es el unico
cliente permitido, jamas el navegador del usuario final.

Cola de 1 solicitud concurrente (docs/AI_MODEL_ODOO_CONFIG.md §8): el host
comparte CPU con dev/test, asi que un lock simple evita que varias
solicitudes de IA compitan al mismo tiempo y degraden el resto del sistema.
"""
import json
import logging
import threading

import requests

_logger = logging.getLogger(__name__)

# Ollama corre en el HOST (fuera de Docker), no dentro del contenedor de
# Odoo -- 127.0.0.1 aqui dentro apuntaria al propio contenedor. Ver
# docker-compose.yml (extra_hosts: host.docker.internal:host-gateway).
OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
DEFAULT_TIMEOUT = 60  # segundos -- consultas de texto son cortas (num_ctx bajo, §4)
# Imagenes reales tardaron 93-242s incluso redimensionadas (medido
# 2026-07-27, ver docs/AI_MODEL_ODOO_CONFIG.md §9.2) -- margen generoso.
VISION_TIMEOUT = 300

_inference_lock = threading.Lock()

# NOTA IMPORTANTE sobre concurrencia entre workers: este threading.Lock()
# solo protege dentro de un mismo proceso Python. Con workers=5 (dev),
# NO evita que 2 workers distintos llamen a Ollama al mismo tiempo -- eso
# es una limitacion conocida y aceptada para las consultas de texto
# (ai_inventory_query, costo bajo). Para el caso de vision (6.7GB de pico
# por solicitud, ver §9.2), la serializacion real NO depende de este lock:
# depende de que el procesamiento corre via cron (image_quote_processor.py),
# y Odoo garantiza que una misma entrada de ir.cron no corre dos veces en
# paralelo (locking propio a nivel de base de datos) -- eso es lo que
# realmente evita que 2 imagenes se procesen a la vez, no este Lock.


class OllamaError(Exception):
    """El modelo no respondio, tardo demasiado, o devolvio JSON invalido/con forma inesperada."""


def generate_structured(model, prompt, json_schema, temperature=0.0, num_ctx=2048,
                         timeout=DEFAULT_TIMEOUT, images=None):
    """
    Llama a Ollama pidiendo un JSON que cumpla json_schema (format=<schema>,
    no el string generico "json" -- la version generica demostro perdida
    silenciosa de datos en pruebas reales, ver docs/AI_MODEL_ODOO_CONFIG.md §5.3).

    images: lista opcional de strings base64 (sin el prefijo data:...) para
    modelos de vision.

    Devuelve el objeto ya parseado (dict o list segun el schema). Lanza
    OllamaError si la respuesta no es JSON valido -- nunca devuelve texto
    crudo silenciosamente como si fuera un resultado valido.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "format": json_schema,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": num_ctx},
    }
    if images:
        payload["images"] = images

    with _inference_lock:
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            _logger.warning("Ollama no respondio (%s): %s", model, exc)
            raise OllamaError("El modelo de IA local no respondio a tiempo.") from exc

    raw = resp.json().get("response", "")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        _logger.warning("Ollama devolvio JSON invalido para modelo %s: %r", model, raw)
        raise OllamaError("El modelo de IA local devolvio una respuesta no valida.") from exc

    return parsed
