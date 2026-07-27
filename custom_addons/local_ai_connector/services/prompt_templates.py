# -*- coding: utf-8 -*-
"""
Plantillas de prompt versionadas para local_ai_connector.

Regla de gobernanza (docs/OLLAMA_MIGRATION_PLAN.md §4 / docs/AI_MODEL_ODOO_CONFIG.md):
cualquier cambio a estas plantillas debe commitearse antes de usarse contra
datos reales. No editar en caliente en produccion.

Regla de terminologia inquebrantable: el unico termino permitido para la
cantidad fisica de un producto es 'A la mano' (On Hand). Nunca "disponible",
"stock" ni "existencias".

Leccion aplicada aqui (docs/AI_MODEL_ODOO_CONFIG.md §5.3): pedir un schema
JSON solo en el texto del prompt no es confiable -- se fuerza ademas con el
parametro `format` de la API de Ollama como un JSON Schema real, no el
string generico "json".
"""

INVENTORY_QUERY_VERSION = "v2"

# El modelo NUNCA redacta el numero final ni el nombre exacto del producto
# -- solo traduce la pregunta en lenguaje natural a una consulta
# estructurada. La cantidad real la calcula Odoo (stock.quant) y la
# respuesta final la arma Python de forma determinista (ver
# inventory_nl_resolver.py) -- el LLM nunca es la fuente de verdad de un
# numero de inventario (regla explicita del documento de diseño).
INVENTORY_QUERY_PROMPT = """Eres un asistente de inventario para MedicineDepot, una farmacia que opera
sobre Odoo 19.

REGLA INQUEBRANTABLE: el unico termino permitido para referirte a la cantidad
fisica de un producto es "A la mano" (On Hand). Nunca uses "disponible",
"stock" ni "existencias", ni en espanol ni en ingles, bajo ninguna
circunstancia -- ni siquiera en esta respuesta.

No conoces cantidades reales de ningun producto. Tu unica tarea es identificar
a que producto se refiere la pregunta del usuario, para que el sistema (no tu)
consulte la cantidad real despues.

Pregunta del usuario:
{question}

IMPORTANTE: "producto_mencionado" debe ser SOLO el nombre, marca o codigo del
producto, tal cual aparece en la pregunta -- nunca una frase completa ni una
descripcion de lo que el usuario pidio. No agregues palabras como "producto",
"codigo de barras" ni ninguna otra que no sea parte del identificador mismo.

Ejemplos:
- Pregunta: "cuanto paracetamol hay a la mano?"
  -> producto_mencionado: "paracetamol"
- Pregunta: "cuanto hay del producto con codigo de barras 7501234567890?"
  -> producto_mencionado: "7501234567890"   (SOLO el numero, no la frase completa)
- Pregunta: "hay medicinas?"
  -> aclaracion_necesaria: true, producto_mencionado: null

Si la pregunta menciona un producto identificable (nombre, marca, o codigo),
devuelve SOLO ese identificador, sin corregirlo ni completarlo. Si la
pregunta es ambigua, no se refiere a ningun producto, o menciona mas de uno
a la vez, marca que hace falta aclaracion en vez de adivinar."""

INVENTORY_QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "producto_mencionado": {"type": ["string", "null"]},
        "aclaracion_necesaria": {"type": "boolean"},
    },
    "required": ["producto_mencionado", "aclaracion_necesaria"],
}
