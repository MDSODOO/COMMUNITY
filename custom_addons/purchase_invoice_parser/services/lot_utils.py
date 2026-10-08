import re
from datetime import date
from typing import Optional

LOT_CADUCIDAD_TRAIL_RE = re.compile(
    r'(?i)\s*fecha(?:\s+de)?\s+caducidad.*$'
)

_MONTHS_ES = {
    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12,
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5,
    'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9,
    'octubre': 10, 'noviembre': 11, 'diciembre': 12,
}


def clean_lot_name(raw: str) -> str:
    """Limpia un nombre de lote extrayendo prefijos 'Lote:' y sufijos de caducidad."""
    lot = (raw or '').strip()
    if not lot:
        return ''
    lot = re.sub(r'(?i)^lote[:\s-]*', '', lot).strip()
    lot = LOT_CADUCIDAD_TRAIL_RE.sub('', lot).strip(" :;-")
    lot = re.sub(r'(?i)fecha$', '', lot).strip(" :;-")
    return lot


def parse_date(day_s, mon_s, year_s) -> Optional[date]:
    """Parsea una fecha con mes numérico o nombre español abreviado."""
    mon_s = (mon_s or '').lower()
    if mon_s.isdigit():
        try:
            mon = int(mon_s)
        except ValueError:
            return None
    else:
        mon = _MONTHS_ES.get(mon_s[:3]) or _MONTHS_ES.get(mon_s)
    if not mon:
        return None
    try:
        year = int(year_s)
        if year < 100:
            year += 2000
        return date(year, mon, int(day_s))
    except (ValueError, TypeError):
        return None
