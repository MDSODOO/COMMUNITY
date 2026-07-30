# -*- coding: utf-8 -*-
"""
Matching de producto para renglones extraidos de imagen.

NO reutiliza ProductMatcher de purchase_invoice_parser a proposito: ese
matcher filtra candidatos por purchase_ok=True (contexto de compra a
proveedores). Aqui el contexto es una cotizacion de VENTA a un cliente
final -- se necesita sale_ok=True. Reutilizar la clase de compras
introduciria un bug sutil (productos vendibles pero no comprables
quedarian invisibles, o viceversa). Mismo criterio de matching
(barcode/default_code exacto, nombre ilike como fallback), pero
implementacion propia con el filtro correcto.

Mejoras 2026-07-28 al paso de nombre (barcode/default_code SIN CAMBIOS):

1. Normalizacion de texto (`_normalize`): minusculas + sin acentos +
   espacios colapsados, aplicada al texto detectado antes del `ilike`.
   No es estrictamente necesaria para el propio `ilike`: Odoo activa
   automaticamente `unaccent()` en AMBOS lados de cualquier comparacion
   ilike/=ilike en cuanto la extension de Postgres esta instalada (ver
   odoo/orm/fields_textual.py, `has_unaccent`) -- por eso basta con tener
   la extension instalada (ver hooks.py / migrations/19.0.1.1.0) para que
   el `ilike` de mas abajo ya ignore acentos. Normalizar tambien en
   Python es defensa en profundidad (funciona igual si por alguna razon
   la extension no estuviera instalada) y ademas limpia espacios extra
   que a veces mete el modelo de vision.

2. Fallback de fuzzy matching (`_name_trgm_fallback`, requiere pg_trgm):
   si el `ilike` normalizado no encuentra NINGUN candidato, se intenta
   una busqueda por similitud de trigramas (`similarity()`) contra el
   nombre completo (sin el corte a 40 caracteres del paso 2), con una
   confianza menor y method='name_trgm' para que quede trazable que
   producto se encontro por esta via. Esto tolera tanto errores de OCR-
   vision de 1-2 letras como texto donde el dato distintivo (mg/ml,
   presentacion) queda fuera de los primeros 40 caracteres.

   El caso de 2+ candidatos por ilike (ambiguo) NO dispara este fallback
   a proposito: ahi ya existe una decision deliberada de dejarlo para
   revision manual del staff en vez de adivinar; el fallback solo aplica
   cuando ilike no propuso NADA.
"""
import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")

# Umbral de similarity() elegido empiricamente contra el catalogo real de
# esta DB (ver scripts/ collateral de verificacion, 2026-07-28): con
# nombres tipicos de 15-40 caracteres, 0.3 alcanza para reconocer un
# typo de 1 letra sin generar demasiados falsos positivos entre
# productos distintos de la misma familia/laboratorio. Si en produccion
# se ve demasiado ruido (falsos positivos) o al reves (no encuentra
# nada), este es el primer valor a ajustar.
NAME_TRGM_THRESHOLD = 0.3


def _normalize(text):
    """Minusculas, sin acentos, espacios repetidos colapsados a uno solo."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return _WHITESPACE_RE.sub(" ", without_accents).strip().lower()


def _name_trgm_fallback(env, normalized_text):
    """Busca el producto vendible mas parecido por similitud de trigramas.

    Requiere las extensiones pg_trgm + unaccent instaladas (ver hooks.py
    y migrations/19.0.1.1.0/post-migrate.py). Si no lo estan -- por
    ejemplo justo despues de un `-u` sin haber reiniciado el contenedor,
    ver nota en hooks.py -- se degrada a "sin match" sin lanzar
    excepcion, misma garantia que el resto de match_product.

    product_template.name es un campo traducido (jsonb): se compara
    contra el idioma del usuario/contexto con fallback a en_US.
    """
    registry = env.registry
    if not normalized_text or not getattr(registry, "has_trigram", False) \
            or not getattr(registry, "has_unaccent", False):
        return env["product.product"].browse()

    lang = env.context.get("lang") or "en_US"
    env.cr.execute(
        """
        SELECT id FROM (
            SELECT
                pp.id AS id,
                similarity(
                    unaccent(lower(COALESCE(pt.name ->> %(lang)s, pt.name ->> 'en_US', ''))),
                    %(text)s
                ) AS sim
            FROM product_product pp
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE pt.sale_ok = true
              AND pp.active = true
              AND pt.active = true
        ) scored
        WHERE sim > %(threshold)s
        ORDER BY sim DESC
        LIMIT 1
        """,
        {"lang": lang, "text": normalized_text, "threshold": NAME_TRGM_THRESHOLD},
    )
    row = env.cr.fetchone()
    if not row:
        return env["product.product"].browse()
    return env["product.product"].sudo().browse(row[0])


def match_product(env, text_detected):
    """
    Devuelve un dict: {product, confidence, method, status}.
    status: 'matched' o 'not_found' (nunca lanza excepcion).
    """
    Product = env["product.product"].sudo()
    text = (text_detected or "").strip()
    text_norm = _normalize(text)

    # 1. Codigo de barras exacto, si el texto es puramente numerico o lo
    # contiene como token aislado (fotos reales a veces traen el codigo
    # junto al nombre, ver hallazgos de docs/AI_MODEL_ODOO_CONFIG.md §7.1).
    # Sin cambios respecto a la version anterior.
    digit_tokens = re.findall(r"\d{6,}", text)
    for token in digit_tokens:
        product = Product.search([("barcode", "=", token)], limit=1)
        if product:
            return {"product": product, "confidence": 1.0, "method": "barcode_exact", "status": "matched"}
        product = Product.search([("default_code", "=ilike", token)], limit=1)
        if product:
            return {"product": product, "confidence": 0.9, "method": "default_code", "status": "matched"}

    # 2. Nombre, con sale_ok -- solo catalogo vendible a clientes. Texto
    # normalizado (acentos/mayusculas/espacios) antes del ilike.
    if text_norm:
        candidates = Product.search([
            ("name", "ilike", text_norm[:40]),
            ("sale_ok", "=", True),
        ], limit=2)
        if len(candidates) == 1:
            return {"product": candidates, "confidence": 0.6, "method": "name_ilike", "status": "matched"}
        # 2+ candidatos = ambiguo -- se trata igual que "no encontrado": el
        # staff decide manualmente en la revision, no se adivina cual.

        # 3. Fallback de fuzzy matching (pg_trgm) -- solo cuando ilike no
        # propuso NINGUN candidato. Usa el texto completo (sin el corte a
        # 40 caracteres de arriba) para no perder el dato distintivo si
        # el modelo de vision antepuso texto de relleno.
        if len(candidates) == 0:
            fuzzy_product = _name_trgm_fallback(env, text_norm)
            if fuzzy_product:
                return {"product": fuzzy_product, "confidence": 0.4, "method": "name_trgm", "status": "matched"}

    return {"product": Product.browse(), "confidence": 0.0, "method": "unresolved", "status": "not_found"}
