"""
Servicio de parseo de archivos Excel para importación de costos.
Référence: purchase_invoice_parser/services/
"""
import base64
import io
import logging
from dataclasses import dataclass, field
from typing import Optional

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import xlrd
except ImportError:
    xlrd = None


@dataclass
class CostImportLine:
    """Representa una línea procesada del archivo Excel"""
    row_number: int
    barcode: Optional[str] = None
    product_name: Optional[str] = None
    cost: Optional[float] = None
    status: str = 'error'  # 'ok', 'no_barcode', 'invalid_cost', 'error'
    error: Optional[str] = None


@dataclass
class CostImportResult:
    """Resultado del parseo de archivo Excel"""
    lines: list = field(default_factory=list)  # list[CostImportLine]
    total: int = 0
    valid: int = 0
    errors: list = field(default_factory=list)


class QuifaCostParser:
    """Parsea archivos Excel de costos Quifamesa"""

    def __init__(self, env=None):
        self.env = env

    @staticmethod
    def _col_index(col_ref, headers):
        """
        Convierte letra de columna (A, B, C...) o nombre de encabezado a índice 0-based.

        Args:
            col_ref: "A", "B", "C" o nombre del encabezado
            headers: lista de encabezados

        Returns:
            índice 0-based o None

        Raises:
            UserError si no encuentra la columna
        """
        if not col_ref:
            return None

        col_ref = col_ref.strip()

        # Intentar como letra de columna (A, B, C, ...)
        if len(col_ref) <= 2 and col_ref.isalpha():
            idx = 0
            for c in col_ref.upper():
                idx = idx * 26 + (ord(c) - ord('A'))
            return idx

        # Intentar como nombre de encabezado
        col_upper = col_ref.upper()
        for i, h in enumerate(headers):
            if h and str(h).strip().upper() == col_upper:
                return i

        available = ', '.join(str(h) for h in headers if h)
        raise UserError(
            f'No se encontró la columna "{col_ref}". Columnas disponibles: {available}'
        )

    @staticmethod
    def _normalize_barcode(raw_value):
        """
        Normaliza código de barras:
        - Convierte números a string sin notación científica
        - Elimina espacios
        - Retorna None si es inválido

        Args:
            raw_value: valor crudel del Excel (int, float, str, None)

        Returns:
            barcode normalizado o None
        """
        if not raw_value:
            return None

        # Manejo de valores numéricos
        if isinstance(raw_value, (int, float)):
            try:
                # Convertir a int primero para evitar notación científica
                bc = str(int(raw_value))
            except (ValueError, OverflowError):
                bc = str(raw_value)
        else:
            bc = str(raw_value).strip()

        # Remover trailing .0
        if bc.endswith('.0'):
            bc = bc[:-2]

        # Validar longitud mínima (códigos de barras típicos >= 8)
        if len(bc) < 4:
            return None

        return bc

    @staticmethod
    def _parse_cost(raw_value):
        """
        Parsea y valida un valor de costo.

        Args:
            raw_value: valor del costo (float, int, str, None)

        Returns:
            tupla (cost: float|None, error: str|None)
        """
        if not raw_value and raw_value != 0:
            return None, 'Costo vacío'

        try:
            cost = float(raw_value)
        except (ValueError, TypeError):
            return None, f'Costo inválido: "{raw_value}"'

        if cost < 0:
            return None, f'Costo negativo: {cost}'

        if cost == 0:
            return None, 'Costo es cero'

        return cost, None

    def read_excel(self, file_binary, filename):
        """
        Lee archivo Excel (XLS o XLSX).

        Args:
            file_binary: contenido binario en base64
            filename: nombre del archivo

        Returns:
            list de listas con valores de celdas

        Raises:
            UserError si hay error al leer
        """
        try:
            data = base64.b64decode(file_binary)
        except Exception as exc:
            raise UserError(f'No se pudo decodificar el archivo: {exc}')

        fname = (filename or '').lower()

        # Archivo XLS (antiguo)
        if fname.endswith('.xls') and not fname.endswith('.xlsx'):
            if not xlrd:
                raise UserError('Se requiere librería xlrd para archivos .xls')
            try:
                book = xlrd.open_workbook(file_contents=data)
                sheet = book.sheet_by_index(0)
                return [sheet.row_values(r) for r in range(sheet.nrows)]
            except Exception as exc:
                raise UserError(f'Error al leer archivo XLS: {exc}')

        # Archivo XLSX (moderno)
        else:
            if not openpyxl:
                raise UserError('Se requiere librería openpyxl para archivos .xlsx')
            try:
                wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
                ws = wb.active
                rows = [list(row) for row in ws.iter_rows(values_only=True)]
                wb.close()
                return rows
            except Exception as exc:
                raise UserError(f'Error al leer archivo XLSX: {exc}')

    def parse(self, file_binary, filename, col_barcode='A', col_cost='H', col_name='C', header_row=1):
        """
        Parsea archivo Excel y extrae costos.

        Args:
            file_binary: contenido binario en base64
            filename: nombre del archivo
            col_barcode: columna con código de barras (ej: 'A')
            col_cost: columna con costo (ej: 'H')
            col_name: columna con descripción (ej: 'C')
            header_row: número de fila de encabezados (1-based)

        Returns:
            CostImportResult con líneas y estadísticas
        """
        result = CostImportResult()

        # Leer archivo
        try:
            rows = self.read_excel(file_binary, filename)
        except UserError:
            raise

        if not rows:
            raise UserError('El archivo está vacío')

        # Validar fila de encabezados
        header_idx = header_row - 1
        if header_idx >= len(rows):
            raise UserError(f'La fila de encabezados ({header_row}) excede el total de filas ({len(rows)})')

        headers = rows[header_idx]

        # Resolver índices de columnas
        try:
            idx_bc = self._col_index(col_barcode, headers)
            idx_cost = self._col_index(col_cost, headers)
            idx_name = self._col_index(col_name, headers) if col_name else None
        except UserError:
            raise

        # Procesar líneas de datos
        for row_num, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
            try:
                # Extraer barcode
                bc_raw = row[idx_bc] if idx_bc < len(row) else None
                bc = self._normalize_barcode(bc_raw)
                if not bc:
                    result.lines.append(CostImportLine(
                        row_number=row_num,
                        barcode=str(bc_raw) if bc_raw else None,
                        status='no_barcode',
                        error='Código de barras vacío o inválido'
                    ))
                    continue

                # Extraer costo
                cost_raw = row[idx_cost] if idx_cost < len(row) else None
                cost, cost_error = self._parse_cost(cost_raw)
                if cost is None:
                    result.lines.append(CostImportLine(
                        row_number=row_num,
                        barcode=bc,
                        status='invalid_cost',
                        error=cost_error
                    ))
                    continue

                # Extraer nombre (opcional)
                name = ''
                if idx_name is not None and idx_name < len(row) and row[idx_name]:
                    name = str(row[idx_name]).strip()

                # Línea válida
                result.lines.append(CostImportLine(
                    row_number=row_num,
                    barcode=bc,
                    product_name=name,
                    cost=cost,
                    status='ok'
                ))
                result.valid += 1

            except Exception as exc:
                _logger.warning(f'Error procesando fila {row_num}: {exc}')
                result.lines.append(CostImportLine(
                    row_number=row_num,
                    status='error',
                    error=str(exc)
                ))

        result.total = len(result.lines)
        return result
