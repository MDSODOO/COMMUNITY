# -*- coding: utf-8 -*-
"""
Utilidades compartidas para parseo de archivos Excel.
Sin estado ni dependencias del ORM — reutilizable por todos los wizards del módulo.
"""
import base64
import io
import logging

_logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import xlrd
except ImportError:
    xlrd = None


def normalize_barcode(raw, strip_zeros=False):
    """
    Normaliza un valor de celda Excel a string de código de barras.

    Orden de operaciones:
    1. int/float → str(int(raw)) para evitar notación científica
    2. Elimina sufijo '.0' de conversiones a string
    3. Limpia espacios/guiones/dos puntos internos
    4. Rechaza valores que no sean enteramente numéricos: un código de barras
       válido solo contiene dígitos. Esto descarta filas de marca/leyenda del
       Excel (ej: "ACCORD", "PISA", "I (Farmater)") que de otro modo se
       colarían como productos.
    5. Valida longitud mínima de 4 chars ANTES de aplicar strip (preserva
       barcodes con ceros iniciales cuyo valor normalizado sería válido)
    6. Aplica lstrip('0') solo si strip_zeros=True

    Returns: barcode normalizado (str) o None si es inválido.
    """
    if not raw and raw != 0:
        return None

    if isinstance(raw, (int, float)):
        try:
            bc = str(int(raw))
        except (ValueError, OverflowError):
            bc = str(raw)
    else:
        bc = str(raw).strip()

    if bc.endswith('.0'):
        bc = bc[:-2]

    # Step 28: remover espacios internos y caracteres especiales no numéricos
    # (ej: "502 896" → "502896", "EAN-13:502896" → "502896")
    import re as _re
    bc = _re.sub(r'[\s\-:\./]', '', bc)

    # Un código de barras válido es enteramente numérico. Rechazar filas de
    # marca/leyenda del Excel (ej: "ACCORD", "PISA", "I (Farmater)") que pasarían
    # el filtro de longitud y se convertirían en productos basura.
    if not bc.isdigit():
        return None

    # Validar longitud ANTES del strip para no descartar barcodes con ceros iniciales
    if len(bc) < 4:
        return None

    if strip_zeros:
        stripped = bc.lstrip('0')
        if not stripped:
            return None
        return stripped

    return bc


def parse_number(raw):
    """
    Convierte un valor de celda Excel a float de forma tolerante.

    openpyxl con data_only=True devuelve floats nativos para celdas numéricas,
    pero MUCHOS catálogos de proveedor exportan los precios como TEXTO con
    formato de moneda mexicano: "$1,234.50", "1,234.50", "1.234,50", "12,50".
    Un simple float() falla con ValueError en todos esos casos y el wizard
    descartaba la fila en silencio — provocando que NINGÚN precio se cargara.

    Reglas de desambiguación (sesgadas a formato MX):
    - Tipos numéricos → float() directo.
    - Se eliminan símbolos de moneda, espacios (incl. NBSP) y letras.
    - Si hay punto Y coma: el ÚLTIMO separador es el decimal; el otro es de
      miles ("1,234.50" → 1234.50 / "1.234,50" → 1234.50).
    - Solo coma: se trata como separador de miles salvo que parezca decimal
      (una sola coma seguida de exactamente 2 dígitos, ej "12,50" → 12.50).
    - Solo punto o solo dígitos: float() directo.

    Returns: float, o None si no se puede interpretar como número.
    """
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)

    import re as _re
    s = str(raw).replace('\xa0', '').strip()
    if not s:
        return None
    # Conservar solo dígitos, separadores y signo negativo
    s = _re.sub(r'[^0-9,.\-]', '', s)
    if not s or s in ('-', '.', ','):
        return None

    has_dot = '.' in s
    has_comma = ',' in s

    if has_dot and has_comma:
        if s.rfind(',') > s.rfind('.'):
            # coma es decimal, punto es miles → "1.234,50"
            s = s.replace('.', '').replace(',', '.')
        else:
            # punto es decimal, coma es miles → "1,234.50"
            s = s.replace(',', '')
    elif has_comma:
        parts = s.split(',')
        # "12,50" → decimal; "1,234" / "100,000" → miles
        if len(parts) == 2 and len(parts[1]) == 2:
            s = s.replace(',', '.')
        else:
            s = s.replace(',', '')

    try:
        return float(s)
    except ValueError:
        return None


def col_index(col_ref, headers):
    """
    Convierte letra de columna (A, B, ..., Z, AA, ...) o nombre de encabezado
    a índice 0-based.

    Raises UserError si col_ref no vacío y no se encuentra.
    Returns None si col_ref es vacío/None.
    """
    from odoo.exceptions import UserError

    if not col_ref:
        return None
    col_ref = col_ref.strip()

    if len(col_ref) <= 2 and col_ref.isalpha():
        idx = 0
        for c in col_ref.upper():
            idx = idx * 26 + (ord(c) - ord('A'))
        return idx

    col_upper = col_ref.upper()
    for i, h in enumerate(headers):
        if h and str(h).strip().upper() == col_upper:
            return i

    available = ', '.join(str(h) for h in headers if h)
    raise UserError(
        f'No se encontró la columna "{col_ref}". '
        f'Columnas encontradas: {available}'
    )


def read_excel(file_binary, filename, sheet_name=None):
    """
    Lee un archivo Excel (XLS o XLSX) y devuelve todas las filas como
    lista de listas de valores nativos de Python.

    Args:
        file_binary: contenido del archivo codificado en base64
        filename:    nombre del archivo (usado para detectar extensión)
        sheet_name:  conservado por compatibilidad; siempre se usa la primera hoja

    Raises UserError en caso de error de lectura o librería ausente.
    """
    from odoo.exceptions import UserError

    try:
        data = base64.b64decode(file_binary)
    except Exception as exc:
        raise UserError(f'No se pudo decodificar el archivo: {exc}')

    fname = (filename or '').lower()

    if fname.endswith('.xls') and not fname.endswith('.xlsx'):
        if not xlrd:
            raise UserError(
                'Se requiere xlrd para archivos .xls. '
                'Instalar con: pip install xlrd'
            )
        try:
            book = xlrd.open_workbook(file_contents=data)
            if not book.nsheets:
                raise UserError('El archivo XLS no contiene hojas de Excel.')
            sheet = book.sheet_by_index(0)
            if not sheet.nrows or not any(
                any(cell not in (None, '') for cell in sheet.row_values(r))
                for r in range(sheet.nrows)
            ):
                raise UserError('La primera hoja del archivo XLS está vacía.')
            return [sheet.row_values(r) for r in range(sheet.nrows)]
        except UserError:
            raise
        except Exception as exc:
            raise UserError(f'Error al leer archivo XLS: {exc}')
    else:
        if not openpyxl:
            raise UserError(
                'Se requiere openpyxl para archivos .xlsx. '
                'Instalar con: pip install openpyxl'
            )
        try:
            wb = openpyxl.load_workbook(
                io.BytesIO(data), read_only=True, data_only=True
            )
            worksheets = wb.worksheets
            if not worksheets:
                raise UserError('El archivo XLSX no contiene hojas de Excel.')
            ws = worksheets[0]
            rows = [list(row) for row in ws.iter_rows(values_only=True)]
            wb.close()
            if not rows or not any(
                any(cell not in (None, '') for cell in row)
                for row in rows
            ):
                raise UserError('La primera hoja del archivo XLSX está vacía.')
            return rows
        except UserError:
            raise
        except Exception as exc:
            raise UserError(f'Error al leer archivo XLSX: {exc}')
