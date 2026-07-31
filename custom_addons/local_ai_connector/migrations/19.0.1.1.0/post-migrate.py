# -*- coding: utf-8 -*-
"""
Migration 19.0.1.1.0 -- Instala las extensiones de Postgres 'unaccent' y
'pg_trgm' que necesita el matching de producto por imagen mejorado
(services/image_quote_matcher.py): normalizacion sin acentos + fallback
de fuzzy matching por similitud de trigramas.

Esta migracion replica `post_init_hook` (ver ../../hooks.py) para que la
instalacion de extensiones se aplique tambien en instancias donde
local_ai_connector ya estaba instalado -- `post_init_hook` solo corre en
un `install` nuevo, no en un `-u`/upgrade de un modulo ya instalado (ver
odoo/modules/loading.py), asi que sin esta migracion una DB existente
nunca ejecutaria el CREATE EXTENSION.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    _logger.info(
        "local_ai_connector 19.0.1.1.0: extensiones Postgres 'unaccent' y "
        "'pg_trgm' verificadas/instaladas (matching de cotizacion por imagen)."
    )
