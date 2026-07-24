import re
import xml.etree.ElementTree as ET
import logging
from dataclasses import dataclass, field
from datetime import datetime, date as Date
from typing import Optional

from .addenda_parsers import get_addenda_parser
from .known_rfcs import KnownRFC

# Extrae lote y caducidad embebidos en Descripcion de conceptos BRUDIFARMA:
# "PRODUCT NAME Lote: XXXXXX Fecha de caducidad: DD.MM.YYYY"
_DESCRIPCION_LOT_RE = re.compile(
    r'\s+Lote:\s*([A-Z0-9][A-Z0-9\-\.]{0,29})\s+Fecha\s+de\s+caducidad:\s*'
    r'(\d{1,2})[./](\d{2})[./](\d{4})',
    re.IGNORECASE,
)

_logger = logging.getLogger(__name__)

CFDI_NS = 'http://www.sat.gob.mx/cfd/4'
TFD_NS = 'http://www.sat.gob.mx/TimbreFiscalDigital'
CFDI_VERSION_SOPORTADA = '4.0'

NS = {
    'cfdi': CFDI_NS,
    'tfd': TFD_NS,
}


@dataclass
class CFDILine:
    no_identificacion: str
    descripcion: str
    cantidad: float
    valor_unitario: float
    importe: float
    clave_unidad: str
    unidad: str
    clave_prod_serv: str
    tasa_iva: float
    importe_iva: float
    factor_iva: str = ''        # 'Tasa' | 'Cuota' | 'Exento'
    iva_presente: bool = False  # True si el XML trajo nodo Traslado de IVA
    tasa_ieps: float = 0.0      # Impuesto 003 (IEPS)
    importe_ieps: float = 0.0
    ieps_presente: bool = False
    # Lote/caducidad embebidos en Descripcion (ej. BRUDIFARMA)
    descripcion_lot: str = ''
    descripcion_caducidad: Optional[Date] = None
    descripcion_clean: str = ''  # Descripcion sin el sufijo "Lote: X Fecha: Y"
    barcode_hint: str = ''


@dataclass
class CFDIDocument:
    uuid: Optional[str] = None
    version: str = ''
    serie: Optional[str] = None
    folio: Optional[str] = None
    fecha: Optional[str] = None
    subtotal: float = 0.0
    total: float = 0.0
    moneda: str = 'MXN'
    condiciones_pago: Optional[str] = None
    emisor_rfc: Optional[str] = None
    emisor_nombre: Optional[str] = None
    emisor_regimen: Optional[str] = None
    receptor_rfc: Optional[str] = None
    receptor_nombre: Optional[str] = None
    lines: list = field(default_factory=list)
    parse_errors: list = field(default_factory=list)
    addenda_lots: list = field(default_factory=list)
    has_retenciones: bool = False
    retenciones_total: float = 0.0

    @property
    def folio_completo(self):
        return f"{self.serie or ''}{self.folio or ''}".strip()


class CFDIParser:
    """
    Parsea un CFDI 4.0 (SAT México) desde bytes XML.
    Usa únicamente xml.etree.ElementTree (stdlib — sin dependencias externas).
    """

    def parse_bytes(self, xml_bytes: bytes) -> CFDIDocument:
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as e:
            doc = CFDIDocument()
            doc.parse_errors.append(f"Error al parsear XML: {e}")
            return doc
        return self._extract(root)

    def _extract(self, root: ET.Element) -> CFDIDocument:
        doc = CFDIDocument()

        doc.version = root.get('Version', '')
        if doc.version and doc.version != CFDI_VERSION_SOPORTADA:
            doc.parse_errors.append(
                f"Versión CFDI no soportada: {doc.version!r}. "
                f"Se esperaba {CFDI_VERSION_SOPORTADA}. "
                "Los datos pueden no ser correctos."
            )

        doc.serie = root.get('Serie')
        doc.folio = root.get('Folio')
        doc.fecha = self._parse_fecha(root.get('Fecha') or '', doc)
        doc.subtotal = float(root.get('SubTotal', 0) or 0)
        doc.total = float(root.get('Total', 0) or 0)
        doc.moneda = root.get('Moneda', 'MXN')
        doc.condiciones_pago = root.get('CondicionesDePago')

        emisor = root.find('cfdi:Emisor', NS)
        if emisor is not None:
            doc.emisor_rfc = (emisor.get('Rfc') or '').upper()
            doc.emisor_nombre = emisor.get('Nombre')
            doc.emisor_regimen = emisor.get('RegimenFiscal')

        receptor = root.find('cfdi:Receptor', NS)
        if receptor is not None:
            doc.receptor_rfc = (receptor.get('Rfc') or '').upper()
            doc.receptor_nombre = receptor.get('Nombre')

        tfd = root.find('.//tfd:TimbreFiscalDigital', NS)
        if tfd is not None:
            doc.uuid = tfd.get('UUID')

        # Retenciones a nivel del comprobante
        self._extract_retenciones(root, doc)

        # Addenda por proveedor (se extrae antes de líneas para poder enriquecer estrategias).
        doc.addenda_lots = self._extract_addenda_lots(root, doc)

        # Fallback universal: IVA a nivel comprobante (cualquier proveedor puede usarlo).
        # Se aplica solo cuando el concepto no declara su propio nodo Traslado de IVA.
        fallback_iva = self._extract_comprobante_iva(root)

        doc.lines = self._extract_lines(
            root,
            doc=doc,
            fallback_iva=fallback_iva,
        )

        if not doc.emisor_rfc:
            doc.parse_errors.append("No se encontró RFC del emisor en el CFDI.")
        if not doc.lines:
            doc.parse_errors.append("No se encontraron conceptos en el CFDI.")

        return doc

    @staticmethod
    def _normalize_code(value: str) -> str:
        return (value or '').strip()

    def _extract_addenda_lots(self, root: ET.Element, doc: CFDIDocument):
        addenda_parser = get_addenda_parser(doc.emisor_rfc or '')
        if not addenda_parser:
            return []
        try:
            return addenda_parser.parse(root)
        except Exception as e:
            _logger.warning("Error al parsear Addenda (RFC %s): %s", doc.emisor_rfc, e)
            doc.parse_errors.append(
                f"No se pudo parsear Addenda para RFC {doc.emisor_rfc}: {e}"
            )
            return []

    def _line_extractors(self):
        """
        Router de estrategias por RFC para desacoplar estructuras proveedor-específicas.
        """
        return {
            KnownRFC.BRUDIFARMA: self._extract_lines_brudifarma,
            KnownRFC.QUIFAMESA: self._extract_lines_quifamesa,
        }

    def _extract_lines(self, root: ET.Element, doc: CFDIDocument, fallback_iva=None):
        supplier_rfc = (doc.emisor_rfc or '').upper()
        extractor = self._line_extractors().get(supplier_rfc, self._extract_lines_default)
        return extractor(root, doc=doc, fallback_iva=fallback_iva)

    def _extract_lines_default(self, root: ET.Element, doc: CFDIDocument, fallback_iva=None):
        lines = []
        for concepto in root.findall('.//cfdi:Concepto', NS):
            line = self._parse_concepto(
                concepto,
                fallback_iva=fallback_iva,
            )
            if line:
                lines.append(line)
        return lines

    def _extract_lines_quifamesa(self, root: ET.Element, doc: CFDIDocument, fallback_iva=None):
        """
        QUIFAMESA (QFM861010BL0):
        - Usa estructura estándar en cfdi:Concepto.
        - Toma NoIdentificacion como código principal para matching por barcode.
        """
        lines = []
        for concepto in root.findall('.//cfdi:Concepto', NS):
            barcode = self._normalize_code(concepto.get('NoIdentificacion', ''))
            line = self._parse_concepto(
                concepto,
                fallback_iva=fallback_iva,
                forced_no_identificacion=barcode,
                barcode_hint=barcode,
            )
            if line:
                lines.append(line)
        return lines

    def _extract_lines_brudifarma(self, root: ET.Element, doc: CFDIDocument, fallback_iva=None):
        """
        BRUDIFARMA (BRU971010227):
        - Mantiene parseo fiscal desde Concepto.
        - Enriquece lote/caducidad/cbarra desde Addenda/MATERIAL.
        """
        lines = self._extract_lines_default(root, doc=doc, fallback_iva=fallback_iva)
        if not lines or not doc.addenda_lots:
            return lines

        by_code = {}
        by_barcode = {}
        for lot in doc.addenda_lots:
            code = self._normalize_code(getattr(lot, 'codigo_sap', ''))
            if code:
                by_code.setdefault(code, []).append(lot)
            cbarra = self._normalize_code(getattr(lot, 'cbarra', ''))
            if cbarra:
                by_barcode.setdefault(cbarra, []).append(lot)

        for line in lines:
            key = self._normalize_code(line.no_identificacion)
            candidates = by_code.get(key) or by_barcode.get(key) or []
            if not candidates:
                continue
            addenda_lot = candidates[0]
            if addenda_lot.lote:
                line.descripcion_lot = addenda_lot.lote
            if addenda_lot.caducidad:
                line.descripcion_caducidad = addenda_lot.caducidad
            cbarra = self._normalize_code(getattr(addenda_lot, 'cbarra', ''))
            if cbarra:
                line.barcode_hint = cbarra
                if not line.no_identificacion:
                    line.no_identificacion = cbarra

        return lines

    @staticmethod
    def _parse_fecha(raw: str, doc: CFDIDocument) -> str:
        """Parsea la fecha del CFDI de forma robusta. Retorna string ISO YYYY-MM-DD."""
        if not raw:
            return ''
        try:
            return datetime.fromisoformat(raw).date().isoformat()
        except ValueError:
            # Fallback: truncar a 10 caracteres si tiene al menos esa longitud
            if len(raw) >= 10:
                _logger.warning("Fecha CFDI con formato inesperado: %r — usando truncado", raw)
                return raw[:10]
            doc.parse_errors.append(f"Fecha con formato inesperado: {raw!r}")
            return ''

    @staticmethod
    def _extract_retenciones(root: ET.Element, doc: CFDIDocument):
        """Detecta nodos de Retenciones en el comprobante y los contabiliza."""
        impuestos = root.find('cfdi:Impuestos', NS)
        if impuestos is None:
            return
        retenciones_node = impuestos.find('cfdi:Retenciones', NS)
        if retenciones_node is None:
            return
        doc.has_retenciones = True
        for ret in retenciones_node.findall('cfdi:Retencion', NS):
            try:
                doc.retenciones_total += float(ret.get('Importe') or 0)
            except (TypeError, ValueError):
                pass

    def _parse_concepto(
        self,
        concepto: ET.Element,
        fallback_iva=None,
        forced_no_identificacion: Optional[str] = None,
        barcode_hint: str = '',
    ) -> Optional[CFDILine]:
        try:
            tasa_iva = 0.0
            imp_iva = 0.0
            factor_iva = ''
            iva_presente = False
            tasa_ieps = 0.0
            imp_ieps = 0.0
            ieps_presente = False

            for traslado in concepto.findall('.//cfdi:Traslado', NS):
                impuesto = traslado.get('Impuesto', '')
                if impuesto == '002':  # IVA
                    iva_presente = True
                    factor_iva = (traslado.get('TipoFactor') or '').strip()
                    try:
                        tasa_iva = float(traslado.get('TasaOCuota') or 0)
                    except (TypeError, ValueError):
                        tasa_iva = 0.0
                    try:
                        imp_iva = float(traslado.get('Importe') or 0)
                    except (TypeError, ValueError):
                        imp_iva = 0.0
                elif impuesto == '003':  # IEPS
                    ieps_presente = True
                    try:
                        tasa_ieps = float(traslado.get('TasaOCuota') or 0)
                    except (TypeError, ValueError):
                        tasa_ieps = 0.0
                    try:
                        imp_ieps = float(traslado.get('Importe') or 0)
                    except (TypeError, ValueError):
                        imp_ieps = 0.0

            if not iva_presente and fallback_iva:
                # Algunos XML solo declaran el IVA en cfdi:Impuestos a nivel comprobante,
                # omitiendo el nodo por concepto. Calculamos el importe por concepto
                # desde la base (Importe del concepto) × tasa para no aplicar el total
                # del comprobante a cada línea en facturas multi-concepto.
                iva_presente = True
                tasa_iva = fallback_iva.get('tasa_iva', 0.0)
                factor_iva = fallback_iva.get('factor_iva', '')
                try:
                    base_concepto = float(concepto.get('Importe', 0) or 0)
                    imp_iva = round(base_concepto * tasa_iva, 2)
                except (TypeError, ValueError):
                    imp_iva = fallback_iva.get('importe_iva', 0.0)

            raw_desc = concepto.get('Descripcion', '')
            descripcion_lot, descripcion_caducidad, descripcion_clean = (
                self._extract_descripcion_lot(raw_desc)
            )

            no_identificacion = forced_no_identificacion
            if no_identificacion is None:
                no_identificacion = concepto.get('NoIdentificacion', '')

            return CFDILine(
                no_identificacion=no_identificacion,
                descripcion=raw_desc,
                descripcion_clean=descripcion_clean,
                descripcion_lot=descripcion_lot,
                descripcion_caducidad=descripcion_caducidad,
                cantidad=float(concepto.get('Cantidad', 1) or 1),
                valor_unitario=float(concepto.get('ValorUnitario', 0) or 0),
                importe=float(concepto.get('Importe', 0) or 0),
                clave_unidad=concepto.get('ClaveUnidad', ''),
                unidad=concepto.get('Unidad', ''),
                clave_prod_serv=concepto.get('ClaveProdServ', ''),
                tasa_iva=tasa_iva,
                importe_iva=imp_iva,
                factor_iva=factor_iva,
                iva_presente=iva_presente,
                tasa_ieps=tasa_ieps,
                importe_ieps=imp_ieps,
                ieps_presente=ieps_presente,
                barcode_hint=barcode_hint,
            )
        except (ValueError, TypeError) as e:
            _logger.warning("Error al parsear concepto CFDI: %s", e)
            return None

    @staticmethod
    def _extract_comprobante_iva(root: ET.Element):
        """Extrae IVA global de cfdi:Impuestos/cfdi:Traslados (si existe)."""
        tasa_iva = 0.0
        imp_iva = 0.0
        factor_iva = ''
        iva_presente = False
        for traslado in root.findall('./cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado', NS):
            impuesto = traslado.get('Impuesto', '')
            if impuesto != '002':
                continue
            iva_presente = True
            factor_iva = (traslado.get('TipoFactor') or '').strip()
            try:
                tasa_iva = float(traslado.get('TasaOCuota') or 0)
            except (TypeError, ValueError):
                tasa_iva = 0.0
            try:
                imp_iva = float(traslado.get('Importe') or 0)
            except (TypeError, ValueError):
                imp_iva = 0.0
        if not iva_presente:
            return None
        return {
            'tasa_iva': tasa_iva,
            'importe_iva': imp_iva,
            'factor_iva': factor_iva,
        }

    @staticmethod
    def _extract_descripcion_lot(raw_desc: str):
        """
        Extrae lote y caducidad embebidos en Descripcion de conceptos BRUDIFARMA.
        Formato esperado: '... Lote: XXXXXX Fecha de caducidad: DD.MM.YYYY'
        Retorna (lot_name, caducidad, descripcion_sin_sufijo).
        """
        match = _DESCRIPCION_LOT_RE.search(raw_desc)
        if not match:
            return '', None, raw_desc
        lot_name = match.group(1).strip()
        try:
            caducidad = Date(
                int(match.group(4)),
                int(match.group(3)),
                int(match.group(2)),
            )
        except (ValueError, TypeError):
            caducidad = None
        clean = raw_desc[:match.start()].strip()
        return lot_name, caducidad, clean
