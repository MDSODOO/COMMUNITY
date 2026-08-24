# -*- coding: utf-8 -*-
"""Pre-migration 19.0.1.3.0 — Logins duplicados y labels de Studio.

Corre ANTES del schema sync para que:
  1. El índice único res_users_login_key pueda crearse sin fallo.
  2. Los labels de x_studio_branch_office queden normalizados antes
     de que el ORM valide duplicados de field_description.

Ambas operaciones son idempotentes y seguras ante múltiples ejecuciones.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # ── 1. Logins duplicados en res_users ────────────────────────────────────
    # Mantiene el registro con mayor prioridad (active=True, id menor).
    # Sufijo _dup_<id> garantiza unicidad porque el id es PK.
    cr.execute(
        """
        UPDATE res_users
        SET login = login || '_dup_' || id::text
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY login
                           ORDER BY active DESC, id ASC
                       ) AS row_num
                FROM res_users
            ) t
            WHERE t.row_num > 1
        )
        """
    )
    if cr.rowcount:
        _logger.warning(
            "[ai_fields 19.0.1.3.0] %d login(s) duplicado(s) renombrado(s) "
            "con sufijo _dup_<id>. Revisar manualmente: login LIKE '%%_dup_%%'.",
            cr.rowcount,
        )
    else:
        _logger.info(
            "[ai_fields 19.0.1.3.0] Sin logins duplicados — res_users_login_key OK."
        )

    # ── 2. Labels Studio: x_studio_branch_office → 'Sucursal (Oficina)' ─────
    cr.execute(
        """
        UPDATE ir_model_fields
        SET field_description = 'Sucursal (Oficina)'
        WHERE name = 'x_studio_branch_office'
          AND field_description != 'Sucursal (Oficina)'
        """
    )
    if cr.rowcount:
        _logger.info(
            "[ai_fields 19.0.1.3.0] %d fila(s) ir_model_fields → 'Sucursal (Oficina)'.",
            cr.rowcount,
        )
