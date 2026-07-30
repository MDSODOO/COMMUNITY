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
import time

import requests

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Ollama corre en el HOST (fuera de Docker), no dentro del contenedor de
# Odoo -- 127.0.0.1 aqui dentro apuntaria al propio contenedor. Ver
# docker-compose.yml (extra_hosts: host.docker.internal:host-gateway).
OLLAMA_URL = "http://201.132.253.85:11434/api/generate"
DEFAULT_TIMEOUT = 60  # segundos -- consultas de texto son cortas (num_ctx bajo, §4)
# Imagenes reales tardaron 93-242s incluso redimensionadas (medido
# 2026-07-27, ver docs/AI_MODEL_ODOO_CONFIG.md §9.2) -- margen generoso.
VISION_TIMEOUT = 300

# Clave fija para advisory lock de Postgres (64-bit). Funciona entre todos
# los workers de Odoo porque el lock es a nivel de base de datos, no de
# proceso.
OLLAMA_ADVISORY_LOCK_KEY = 4202420242024202

# Circuit breaker para el modelo de vision: si falla N veces seguidas
# se salta el procesamiento durante 5 minutos para evitar OOM.
_VISION_FAILURE_COUNT = 0
_VISION_LAST_FAILURE_TIME = 0.0
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_RESET_TIMEOUT = 300  # 5 minutos

_inference_lock = threading.Lock()

# NOTA IMPORTANTE sobre concurrencia entre workers:
# - threading.Lock() solo protege dentro de un mismo proceso Python
#   (se usa para consultas de texto, costo bajo).
# - PostgreSQL advisory lock (OLLAMA_ADVISORY_LOCK_KEY) protege entre
#   todos los workers para el procesamiento de vision (6.7GB pico por
#   solicitud). Se adquiere via pg_try_advisory_lock() y se libera
#   explicitamente despues de la llamada HTTP a Ollama.
# - Circuit breaker: si el modelo de vision falla 5 veces seguidas, se
#   degrada por 5 minutos y se rechazan solicitudes con OllamaBusyError.


class OllamaBusyError(UserError):
    """Ollama esta procesando otra solicitud (advisory lock ocupado) o el
    modelo de vision esta degradado por errores repetidos."""


def _acquire_ollama_lock(cr, lock_key=OLLAMA_ADVISORY_LOCK_KEY, timeout=300.0):
    """Adquiere un PostgreSQL advisory lock (sesion). Bloquea hasta
    `timeout` segundos, reintentando cada 1s. Devuelve True si lo
    obtiene, False si expira el tiempo."""
    start = time.time()
    while time.time() - start < timeout:
        cr.execute("SELECT pg_try_advisory_lock(%s)", [lock_key])
        acquired = cr.fetchone()[0]
        if acquired:
            return True
        time.sleep(1.0)
    return False


def _release_ollama_lock(cr, lock_key=OLLAMA_ADVISORY_LOCK_KEY):
    """Libera el advisory lock de Postgres."""
    cr.execute("SELECT pg_advisory_unlock(%s)", [lock_key])


def _is_vision_degraded():
    global _VISION_FAILURE_COUNT, _VISION_LAST_FAILURE_TIME
    if _VISION_FAILURE_COUNT >= CIRCUIT_BREAKER_THRESHOLD:
        if time.time() - _VISION_LAST_FAILURE_TIME >= CIRCUIT_BREAKER_RESET_TIMEOUT:
            _VISION_FAILURE_COUNT = 0
            return False
        return True
    return False


def _record_vision_success():
    global _VISION_FAILURE_COUNT
    _VISION_FAILURE_COUNT = 0


def _record_vision_failure():
    global _VISION_FAILURE_COUNT, _VISION_LAST_FAILURE_TIME
    _VISION_FAILURE_COUNT += 1
    _VISION_LAST_FAILURE_TIME = time.time()


def _call_ollama_with_retry(payload, timeout, max_retries=3):
    """Llama a Ollama con hasta `max_retries` reintentos y backoff
    exponencial (1s, 2s, 4s...). Registra exito/fallo en el circuit
    breaker. Lanza OllamaError si todos los intentos fallan."""
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
            resp.raise_for_status()
            _record_vision_success()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            _logger.warning(
                "Ollama vision attempt %d/%d failed (%s): %s",
                attempt + 1, max_retries + 1, payload.get("model"), exc,
            )
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    _record_vision_failure()
    raise OllamaError("El modelo de IA local no respondio a tiempo.") from last_exc


class OllamaError(Exception):
    """El modelo no respondio, tardo demasiado, o devolvio JSON invalido/con forma inesperada."""


def generate_structured(model, prompt, json_schema, temperature=0.0, num_ctx=2048,
                         timeout=DEFAULT_TIMEOUT, images=None, priority='high',
                         cr=None):
    """
    Llama a Ollama pidiendo un JSON que cumpla json_schema (format=<schema>,
    no el string generico "json" -- la version generica demostro perdida
    silenciosa de datos en pruebas reales, ver docs/AI_MODEL_ODOO_CONFIG.md §5.3).

    images: lista opcional de strings base64 para modelos de vision.
    priority: 'high' para texto (threading.Lock local al proceso, rapido),
      'low' para vision (PostgreSQL advisory lock entre workers + circuit
      breaker + reintentos). Cuando se pasan images se fuerza priority='low'.
    cr: cursor de base de datos Odoo (requerido para priority='low').

    Devuelve el objeto parseado (dict o list segun el schema). Lanza
    OllamaError si la respuesta no es JSON valido; OllamaBusyError si el
    modelo de vision esta ocupado o degradado.
    """
    is_vision = bool(images)
    if is_vision:
        priority = 'low'

    if is_vision and _is_vision_degraded():
        _logger.warning(
            "Vision model %s is degraded after %d consecutive failures, skipping request",
            model, _VISION_FAILURE_COUNT,
        )
        raise OllamaBusyError(
            "El modelo de vision esta temporalmente fuera de servicio "
            "debido a errores repetidos. Intenta de nuevo en unos minutos."
        )

    if is_vision and not cr:
        raise ValueError(
            "Se requiere un cursor de base de datos (cr) para "
            "llamadas de vision (priority='low')."
        )

    payload = {
        "model": model,
        "prompt": prompt,
        "format": json_schema,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": num_ctx},
    }
    if images:
        payload["images"] = images

    if is_vision:
        _logger.info(
            "Acquiring PostgreSQL advisory lock for vision inference "
            "(model=%s, timeout=%ss)", model, timeout,
        )
        if not _acquire_ollama_lock(cr, timeout=timeout):
            _logger.warning(
                "Could not acquire vision lock within %ss for model %s",
                timeout, model,
            )
            raise OllamaBusyError(
                "El modelo de IA local esta ocupado procesando otra "
                "solicitud. Intenta de nuevo en un momento."
            )
        try:
            resp = _call_ollama_with_retry(payload, timeout)
        finally:
            _release_ollama_lock(cr)
            _logger.info("Released PostgreSQL advisory lock for vision inference")
    else:
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
        if is_vision:
            _record_vision_failure()
        raise OllamaError("El modelo de IA local devolvio una respuesta no valida.") from exc

    return parsed
