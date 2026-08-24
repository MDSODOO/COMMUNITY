# -*- coding: utf-8 -*-
import logging
import warnings

# Suprime DeprecationWarning generados por l10n_mx_edi al importar
# módulos internos de zeep/OpenSSL en ciertas versiones de Odoo 19.
# REVISAR en cada actualización de l10n_mx_edi: si al quitar este bloque
# el servidor arranca sin warnings, eliminar. Si persisten, reportar
# al mantenedor del módulo oficial (OCA / Vauxoo / Odoo SA).
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r".*l10n_mx_edi.*",
)

from . import models

_logger = logging.getLogger(__name__)


def _fix_duplicate_logins(env):
    """Detecta y renombra logins duplicados en res_users.

    Mantiene intacto el registro con mayor prioridad (active=True, id menor)
    y añade sufijo _dup_<id> a los secundarios. Idempotente: logins ya
    renombrados no vuelven a aparecer como duplicados en ejecuciones posteriores.
    """
    try:
        env.cr.execute("""
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
            """)
        if env.cr.rowcount:
            _logger.warning(
                "ai_fields: %d login(s) duplicado(s) renombrado(s) con sufijo _dup_<id>. "
                "Revisar manualmente en res.users.",
                env.cr.rowcount,
            )
        else:
            _logger.info("ai_fields: sin logins duplicados — índice único puede aplicarse.")
    except Exception as exc:
        _logger.warning("ai_fields: error al limpiar logins duplicados: %s", exc)


def post_init_hook(env):
    """Ejecutado al instalar/actualizar el módulo.

    Aplica correcciones de BD que el ORM no puede garantizar:
    - Logins duplicados en res_users (bloquean el índice único)

    El renombramiento de x_studio_branch_office (label duplicado con
    x_studio_branch) lo hace data/field_labels.xml vía ORM — se removió
    de aquí una segunda implementación por SQL crudo que comparaba
    ir_model_fields.field_description (jsonb desde Odoo 19) contra un
    string plano, error que Postgres no perdona ni con el cursor
    envuelto en try/except: aborta la transacción completa para el
    resto del post_init_hook.
    """
    if env.context.get("skip_post_init_hook"):
        return
    _fix_duplicate_logins(env)


def post_load():
    """Hook por proceso (sin env). No tocamos BD aquí."""
    return
