"""
DEPRECIADO: Este módulo es un shim de compatibilidad para la API histórica.
Usar directamente services.pdf_lot_provider.get_provider() en código nuevo.
Candidato a eliminación cuando no exista ningún importador externo.
"""
from .pdf_lot_provider import get_provider


def parse_lots_by_article(pdf_bytes):
    return get_provider('generic').parse(pdf_bytes)


def diagnose(pdf_bytes, max_chars=2000):
    return get_provider('generic').diagnose(pdf_bytes, max_chars=max_chars)
