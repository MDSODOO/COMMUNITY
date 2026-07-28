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
"""
import re


def match_product(env, text_detected):
    """
    Devuelve un dict: {product, confidence, method, status}.
    status: 'matched' o 'not_found' (nunca lanza excepcion).
    """
    Product = env["product.product"].sudo()
    text = (text_detected or "").strip()

    # 1. Codigo de barras exacto, si el texto es puramente numerico o lo
    # contiene como token aislado (fotos reales a veces traen el codigo
    # junto al nombre, ver hallazgos de docs/AI_MODEL_ODOO_CONFIG.md §7.1).
    digit_tokens = re.findall(r"\d{6,}", text)
    for token in digit_tokens:
        product = Product.search([("barcode", "=", token)], limit=1)
        if product:
            return {"product": product, "confidence": 1.0, "method": "barcode_exact", "status": "matched"}
        product = Product.search([("default_code", "=ilike", token)], limit=1)
        if product:
            return {"product": product, "confidence": 0.9, "method": "default_code", "status": "matched"}

    # 2. Nombre, con sale_ok -- solo catalogo vendible a clientes.
    if text:
        candidates = Product.search([
            ("name", "ilike", text[:40]),
            ("sale_ok", "=", True),
        ], limit=2)
        if len(candidates) == 1:
            return {"product": candidates, "confidence": 0.6, "method": "name_ilike", "status": "matched"}
        # 2+ candidatos = ambiguo -- se trata igual que "no encontrado": el
        # staff decide manualmente en la revision, no se adivina cual.

    return {"product": Product.browse(), "confidence": 0.0, "method": "unresolved", "status": "not_found"}
