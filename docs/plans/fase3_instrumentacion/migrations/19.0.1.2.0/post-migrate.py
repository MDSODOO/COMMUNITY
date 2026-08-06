# -*- coding: utf-8 -*-
"""
Migration 19.0.1.2.0 -- Fase 3 de instrumentacion de latencia (2026-07-31).

Este modulo sigue la convencion ya establecida en
migrations/19.0.1.1.0/post-migrate.py de este mismo addon: usar
migrations/<version>/post-migrate.py para pasos que el propio mecanismo de
carga de campos de Odoo NO cubre (ahi la extension de Postgres CREATE
EXTENSION; aqui, una verificacion de sanidad post-carga).

A DIFERENCIA de 19.0.1.1.0, este cambio NO requiere ningun ALTER TABLE
manual: los 5 campos nuevos de esta fase son fields.Float/Datetime/Integer
simples y opcionales (sin required=True, sin default distinto al que Odoo
ya usa para su tipo) --

  - local_ai_query_log.duration_seconds            (Float)
  - local_ai_image_quote_image.duration_seconds     (Float)
  - local_ai_image_quote_request.processing_started_at (Datetime)
  - local_ai_image_quote_request.processing_pid     (Integer)

-- y el propio ORM de Odoo los crea automaticamente (ALTER TABLE ...
ADD COLUMN) durante la carga del modulo, ANTES de que corra este
post-migrate. Ver odoo/addons/base/models/ir_model.py
(BaseModel._auto_init) para la logica que hace esto en cualquier
`-u <modulo>`.

Este script por lo tanto NO hace ningun cambio de esquema por su cuenta --
solo verifica (SELECT contra information_schema, de solo lectura) que las
columnas nuevas efectivamente existan despues de la carga, y deja un log
claro si algo salio distinto a lo esperado (ej. un campo con un nombre
distinto por un typo, o una version de Odoo que cambio el orden
pre/post-migrate). Es deliberadamente conservador: cero DDL propio, cero
riesgo de bloqueo/corrupcion sobre datos reales de cotizaciones.
"""
import logging

_logger = logging.getLogger(__name__)

_EXPECTED_COLUMNS = [
    ("local_ai_query_log", "duration_seconds"),
    ("local_ai_image_quote_image", "duration_seconds"),
    ("local_ai_image_quote_request", "processing_started_at"),
    ("local_ai_image_quote_request", "processing_pid"),
]


def migrate(cr, version):
    missing = []
    for table, column in _EXPECTED_COLUMNS:
        cr.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
            """,
            [table, column],
        )
        if not cr.fetchone():
            missing.append("{}.{}".format(table, column))

    if missing:
        _logger.warning(
            "local_ai_connector 19.0.1.2.0: las siguientes columnas de la "
            "Fase 3 de instrumentacion de latencia NO se encontraron tras "
            "la carga del modulo (revisar modelos/_auto_init): %s",
            ", ".join(missing),
        )
    else:
        _logger.info(
            "local_ai_connector 19.0.1.2.0: columnas de instrumentacion de "
            "latencia (duration_seconds, processing_started_at, "
            "processing_pid) verificadas OK."
        )
