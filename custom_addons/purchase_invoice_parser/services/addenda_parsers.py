import logging
from datetime import date
from dataclasses import dataclass
from typing import Optional, List
import xml.etree.ElementTree as ET

from .known_rfcs import KnownRFC
from .lot_utils import clean_lot_name

_logger = logging.getLogger(__name__)

_NS = {'cfdi': 'http://www.sat.gob.mx/cfd/4'}


@dataclass
class AddendaLot:
    codigo_sap: str
    lote: str
    caducidad: Optional[date]
    cantidad: float
    precio: float
    cbarra: str = ''


class BaseAddendaParser:
    """Interfaz base para parsers de Addenda CFDI identificados por RFC de emisor."""
    rfc: str = ''

    def parse(self, root: ET.Element) -> List[AddendaLot]:
        raise NotImplementedError


class AddendaParserRegistry:
    """Registry con decorador @register para agregar parsers sin tocar get_addenda_parser()."""
    _parsers: dict = {}

    @classmethod
    def register(cls, parser_class):
        instance = parser_class()
        cls._parsers[instance.rfc.upper()] = instance
        return parser_class

    @classmethod
    def get(cls, rfc: str) -> Optional[BaseAddendaParser]:
        return cls._parsers.get((rfc or '').upper())


@AddendaParserRegistry.register
class BrudifarmaAddendaParser(BaseAddendaParser):
    """
    Parser de Addenda para BRUDIFARMA (RFC BRU971010227).

    Extrae nodos <cfdi:MATERIAL> con los atributos:
    CodigoSAP, Lote, Caducidad (DD.MM.YYYY), CBarra, Cantidad, Precio.
    """
    rfc = KnownRFC.BRUDIFARMA

    def parse(self, root: ET.Element) -> List[AddendaLot]:
        lots = []
        addenda = root.find('cfdi:Addenda', _NS)
        if addenda is None:
            _logger.debug("BRUDIFARMA: sin nodo cfdi:Addenda en el CFDI")
            return lots

        materials = addenda.findall('cfdi:MATERIAL', _NS)
        if not materials:
            materials = [
                node for node in addenda.iter()
                if self._local_name(node.tag) == 'MATERIAL'
            ]

        for material in materials:
            lote = clean_lot_name(material.get('Lote') or '')
            if not lote:
                continue

            caducidad = self._parse_caducidad(material.get('Caducidad') or '')

            try:
                cantidad = float((material.get('Cantidad') or '0').replace(',', '.'))
            except ValueError:
                cantidad = 0.0

            try:
                precio = float((material.get('Precio') or '0').replace(',', '.'))
            except ValueError:
                precio = 0.0

            lots.append(AddendaLot(
                codigo_sap=(material.get('CodigoSAP') or '').strip(),
                lote=lote,
                caducidad=caducidad,
                cantidad=cantidad,
                precio=precio,
                cbarra=(material.get('CBarra') or '').strip(),
            ))

        _logger.info("BRUDIFARMA Addenda: %d lote(s) extraídos", len(lots))
        return lots

    @staticmethod
    def _local_name(tag: str) -> str:
        if not tag:
            return ''
        if '}' in tag:
            return tag.rsplit('}', 1)[1]
        return tag

    @staticmethod
    def _parse_caducidad(raw: str) -> Optional[date]:
        """Convierte formato 'DD.MM.YYYY' a datetime.date."""
        if not raw:
            return None
        parts = raw.split('.')
        if len(parts) != 3:
            _logger.warning("Caducidad BRUDIFARMA con formato inesperado: %r", raw)
            return None
        try:
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
        except (ValueError, TypeError):
            _logger.warning("No se pudo parsear caducidad BRUDIFARMA: %r", raw)
            return None


def get_addenda_parser(rfc: str) -> Optional[BaseAddendaParser]:
    """Retorna el parser de Addenda para el RFC dado, o None si no hay implementación."""
    return AddendaParserRegistry.get(rfc)
