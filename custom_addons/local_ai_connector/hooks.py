# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def _ensure_postgres_extensions(cr):
    """Instala (si hace falta) las extensiones de Postgres que usa el
    matching de producto por imagen (`services/image_quote_matcher.py`):

    - `unaccent`: Odoo la detecta automaticamente (ver
      odoo/orm/registry.py `has_unaccent` / odoo/orm/fields_textual.py) y,
      una vez instalada, TODOS los dominios `ilike` del sistema (no solo
      los de este modulo) comparan ignorando acentos -- no requiere
      cambios de codigo aparte de tener la extension instalada. Efecto
      colateral esperado y deseado: busquedas de texto en el resto de
      Odoo (partners, productos, etc.) tambien se vuelven accent-insensitive.
    - `pg_trgm`: habilita `similarity()`, usada como fallback de fuzzy
      matching en `_name_trgm_fallback` cuando el `ilike` normalizado no
      encuentra ningun candidato (tolera 1 error de OCR-vision).

    Ambas son extensiones estandar de contrib de Postgres, no instalan
    nada fuera de la base de datos. Se usa `IF NOT EXISTS` porque este
    hook puede volver a ejecutarse (ver migrations/) sin que sea un error
    si ya estaban instaladas por otro modulo u otra migracion.
    """
    cr.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    _logger.info(
        "local_ai_connector: extensiones Postgres 'unaccent' y 'pg_trgm' "
        "verificadas/instaladas (matching de cotizacion por imagen)."
    )


def post_init_hook(env):
    _ensure_postgres_extensions(env.cr)
    # Nota: `env.registry.has_unaccent` / `has_trigram` se calculan una
    # sola vez al construirse el Registry (odoo/orm/registry.py) y no se
    # recalculan solos dentro de un proceso ya corriendo. Este proyecto
    # ya reinicia el contenedor `odoo` tras cambios de codigo en este
    # modulo (ver instrucciones de despliegue), lo cual reconstruye el
    # Registry desde cero y recoge las extensiones recien creadas -- no
    # se intenta parchear esas banderas en caliente aqui para no depender
    # de simbolos internos/privados de Odoo.
