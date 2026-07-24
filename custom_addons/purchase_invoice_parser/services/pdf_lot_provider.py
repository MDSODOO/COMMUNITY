import io
import logging
import re
from datetime import date

from .lot_utils import clean_lot_name, parse_date

_logger = logging.getLogger(__name__)

_ARTICLE_RE = re.compile(
    r'^\s*(\d{6,14})\s+([A-ZÁÉÍÓÚÑ]{2,10})\s+\d+(?:[.,]\d+)?\s',
    re.IGNORECASE,
)

_LOT_SLASH_RE = re.compile(
    r'([A-Z0-9][A-Z0-9\-\.]{1,30})/(\d{1,2})-([a-záéíóú]{3,12})\.?-(\d{4})/(\d+(?:[.,]\d+)?)',
    re.IGNORECASE,
)

_LOT_KV_RE = re.compile(
    r'lote[:\s]+([A-Z0-9][A-Z0-9\-\.]{1,30}).*?'
    r'(?:cad|caduc|venc|exp)[a-z]*[:\s]+(\d{1,2})[/\-](\d{1,2}|[a-z]{3,12})[/\-](\d{2,4}).*?'
    r'(?:cant|qty|cantidad|piezas?)[:\s]+(\d+(?:[.,]\d+)?)',
    re.IGNORECASE,
)

_LOT_NUM_RE = re.compile(
    r'([A-Z0-9][A-Z0-9\-\.]{1,30})[\s/](\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})[\s/](\d+(?:[.,]\d+)?)',
    re.IGNORECASE,
)

_DISCOUNT_RE = re.compile(
    r'^\s*(?:descuento|desc\.?)\s*[:\-]?\s*\$?\s*(\d+(?:[.,]\d+)?)\s*%?\s*$',
    re.IGNORECASE,
)

_BRUDIFARMA_ARTICLE_RE = re.compile(
    r'^\s*(\d+(?:[.,]\d+)?)\s+[A-Z0-9]{2,4}\s*-\s*[A-ZÁÉÍÓÚÑ]{2,10}\s+\d{8}\s+([A-Z0-9]{4,20})\b',
    re.IGNORECASE,
)

_BRUDIFARMA_LOT_INLINE_RE = re.compile(
    r'lote:\s*([A-Z0-9][A-Z0-9\-\.]{1,30}).*?fecha de caducidad:\s*(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})',
    re.IGNORECASE,
)

_BRUDIFARMA_LOT_LINE_RE = re.compile(
    r'\b([A-Z0-9][A-Z0-9\-\.]{1,30})\s+fecha de caducidad:\s*(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})',
    re.IGNORECASE,
)

_BRUDIFARMA_LOT_ONLY_RE = re.compile(
    r'lote:\s*([A-Z0-9][A-Z0-9\-\.]{1,30})\b',
    re.IGNORECASE,
)

_BRUDIFARMA_DATE_ONLY_RE = re.compile(
    r'^\s*(?:fecha de caducidad:\s*)?(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\s*$',
    re.IGNORECASE,
)

# Quifamesa: líneas de artículo tienen formato  {barcode}/{descripcion}/{unidad}
#            o  {barcode}. {descripcion}  (casos con punto seguido de espacio)
_QUIFAMESA_ARTICLE_RE = re.compile(
    r'^\s*(\d{6,14})\s*[/\.]',
)

# Quifamesa: líneas de lote tienen formato  Lotes: {lote}/{DD}-{mmm}.-{YYYY}/{qty}
# El punto después del mes es opcional (ene. vs ene)
_QUIFAMESA_LOT_RE = re.compile(
    r'Lotes:\s+([A-Z0-9][A-Z0-9\-\.]{1,30})'
    r'/(\d{1,2})-([a-záéíóú]{3,12})\.?-(\d{4})'
    r'/(\d+(?:[.,]\d+)?)',
    re.IGNORECASE,
)


def _extract_text(pdf_bytes):
    """Extrae texto del PDF usando pdfplumber (preferido) o pypdf como fallback."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or '')
        return '\n'.join(text_parts)
    except ImportError:
        pass
    except Exception:
        _logger.debug("pdfplumber no pudo extraer texto; intentando pypdf", exc_info=True)

    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader  # type: ignore
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return '\n'.join((page.extract_text() or '') for page in reader.pages)


class LotParserProvider:
    key = 'base'
    display_name = 'Base'

    def parse(self, pdf_bytes):
        text = _extract_text(pdf_bytes)
        return self._parse_text(text)

    def diagnose(self, pdf_bytes, max_chars=2000):
        return _extract_text(pdf_bytes)[:max_chars]

    def _parse_text(self, text):
        if not (text or '').strip():
            _logger.warning("%s provider: extract_text devolvio texto vacio", self.key)
            return {}

        _logger.info("%s provider: %d caracteres extraidos", self.key, len(text))

        result = {}
        current = None
        pending_discount = 0.0
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            article_match = _ARTICLE_RE.match(line)
            if article_match:
                current = article_match.group(1)
                result.setdefault(current, [])
                pending_discount = 0.0
                continue
            if not current:
                continue

            discount_match = _DISCOUNT_RE.match(line)
            if discount_match:
                try:
                    pending_discount = float(discount_match.group(1).replace(',', '.'))
                except ValueError:
                    pending_discount = 0.0
                continue

            if 'lote' not in line.lower():
                continue

            new_lots = self._parse_lot_line(line)
            if new_lots:
                for lot in new_lots:
                    lot['discount'] = pending_discount
                result[current].extend(new_lots)
                pending_discount = 0.0

        return {key: value for key, value in result.items() if value}

    def _parse_lot_line(self, line):
        patterns = (_LOT_SLASH_RE, _LOT_KV_RE, _LOT_NUM_RE)
        for pattern in patterns:
            lots = []
            for match in pattern.finditer(line):
                name, day, month, year, qty = match.groups()
                lots.append({
                    'name': name.strip(),
                    'expiration_date': parse_date(day, month, year),
                    'quantity': float(qty.replace(',', '.')),
                })
            if lots:
                return lots
        return []


class GenericProvider(LotParserProvider):
    key = 'generic'
    display_name = 'Generico (3 formatos)'


class QuifamesaProvider(GenericProvider):
    key = 'quifamesa'
    display_name = 'Quifamesa'

    def _parse_text(self, text):
        if not (text or '').strip():
            _logger.warning("%s provider: extract_text devolvio texto vacio", self.key)
            return {}

        _logger.info("%s provider: %d caracteres extraidos", self.key, len(text))

        result = {}
        current = None

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            article_match = _QUIFAMESA_ARTICLE_RE.match(line)
            if article_match:
                current = article_match.group(1)
                result.setdefault(current, [])
                continue

            if not current:
                continue

            for lot_match in _QUIFAMESA_LOT_RE.finditer(line):
                name, day, month, year, qty_s = lot_match.groups()
                try:
                    exp = parse_date(day, month, year)
                    qty = float(qty_s.replace(',', '.'))
                except Exception:
                    _logger.warning(
                        "quifamesa: error parseando lote '%s' fecha '%s-%s-%s' qty '%s'",
                        name, day, month, year, qty_s,
                    )
                    exp = None
                    qty = 0.0
                result[current].append({
                    'name': name.strip(),
                    'expiration_date': exp,
                    'quantity': qty,
                    'discount': 0.0,
                })

        return {k: v for k, v in result.items() if v}


class BrudifarmaProvider(LotParserProvider):
    key = 'brudifarma'
    display_name = 'Brudifarma (referencia interna)'

    def _parse_text(self, text):
        if not (text or '').strip():
            _logger.warning("%s provider: extract_text devolvio texto vacio", self.key)
            return {}

        result = {}
        seen = set()
        current_code = None
        current_qty = 0.0
        pending_lot_name = None

        for raw_line in text.splitlines():
            line = (raw_line or '').strip()
            if not line:
                continue

            article_match = _BRUDIFARMA_ARTICLE_RE.match(line)
            if article_match:
                qty_s, code = article_match.groups()
                try:
                    current_qty = float(qty_s.replace(',', '.'))
                except ValueError:
                    current_qty = 0.0
                current_code = code.strip()
                result.setdefault(current_code, [])

            if not current_code:
                lot_only = _BRUDIFARMA_LOT_ONLY_RE.search(line)
                if lot_only:
                    pending_lot_name = clean_lot_name(lot_only.group(1))
                continue

            lot_match = (
                _BRUDIFARMA_LOT_INLINE_RE.search(line)
                or _BRUDIFARMA_LOT_LINE_RE.search(line)
            )
            if lot_match:
                lot_name, day, month, year = lot_match.groups()
                lot_name = clean_lot_name(lot_name)
                if not lot_name:
                    pending_lot_name = None
                    continue
                exp = parse_date(day, month, year)
                key = (current_code, lot_name, exp, current_qty)
                if key not in seen:
                    seen.add(key)
                    result[current_code].append({
                        'name': lot_name,
                        'expiration_date': exp,
                        'quantity': current_qty,
                    })
                pending_lot_name = None
                continue

            lot_only = _BRUDIFARMA_LOT_ONLY_RE.search(line)
            if lot_only:
                pending_lot_name = clean_lot_name(lot_only.group(1))
                continue

            date_only = _BRUDIFARMA_DATE_ONLY_RE.match(line)
            if date_only and pending_lot_name:
                day, month, year = date_only.groups()
                exp = parse_date(day, month, year)
                key = (current_code, pending_lot_name, exp, current_qty)
                if key not in seen:
                    seen.add(key)
                    result[current_code].append({
                        'name': pending_lot_name,
                        'expiration_date': exp,
                        'quantity': current_qty,
                    })
                pending_lot_name = None

        return {key: value for key, value in result.items() if value}


_PROVIDERS = {
    provider.key: provider
    for provider in (GenericProvider(), QuifamesaProvider(), BrudifarmaProvider())
}


def get_provider(key=None):
    return _PROVIDERS.get(key or 'generic', _PROVIDERS['generic'])


def available_providers():
    return [(provider.key, provider.display_name) for provider in _PROVIDERS.values()]
