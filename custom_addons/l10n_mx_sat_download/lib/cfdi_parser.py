# -*- coding: utf-8 -*-
"""
Parser especializado de CFDI 3.3 / 4.0

Extrae toda la información estructurada de un XML de CFDI:
- Datos del comprobante
- Emisor / Receptor
- Conceptos (líneas) con sus impuestos trasladados y retenidos
- Complemento de Timbre Fiscal Digital
- Complemento de Pagos (si aplica)

Diseñado para alimentar la creación automática de account.move + líneas.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from lxml import etree

_logger = logging.getLogger(__name__)

# ============================================================================
# Namespaces soportados
# ============================================================================
CFDI_NAMESPACES = {
    '4.0': {
        'cfdi': 'http://www.sat.gob.mx/cfd/4',
        'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
        'pago20': 'http://www.sat.gob.mx/Pagos20',
    },
    '3.3': {
        'cfdi': 'http://www.sat.gob.mx/cfd/3',
        'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
        'pago10': 'http://www.sat.gob.mx/Pagos',
    },
}

# Catálogo SAT de impuestos → nombre legible
SAT_TAX_MAP = {
    '001': 'ISR',
    '002': 'IVA',
    '003': 'IEPS',
}


# ============================================================================
# Dataclasses para datos parseados
# ============================================================================
@dataclass
class CfdiTax:
    """Impuesto individual de un concepto."""
    tax_type: str          # 'traslado' o 'retencion'
    impuesto: str          # Clave SAT: '001', '002', '003'
    impuesto_name: str     # 'ISR', 'IVA', 'IEPS'
    tipo_factor: str       # 'Tasa', 'Cuota', 'Exento'
    tasa_o_cuota: float    # e.g. 0.160000
    importe: float         # Monto calculado
    base: float            # Base gravable


@dataclass
class CfdiConcepto:
    """Línea de concepto del CFDI."""
    clave_prod_serv: str   # Clave del catálogo SAT de productos/servicios
    clave_unidad: str      # Clave del catálogo SAT de unidades
    no_identificacion: str # Número de identificación del proveedor
    cantidad: float
    unidad: str            # Descripción de la unidad
    descripcion: str
    valor_unitario: float
    importe: float         # cantidad * valor_unitario
    descuento: float       # Descuento sobre la línea
    objeto_imp: str        # '01' No objeto, '02' Sí objeto, '03' Sí obj no obligado
    taxes: list[CfdiTax] = field(default_factory=list)


@dataclass
class CfdiEmisor:
    """Datos del emisor."""
    rfc: str
    nombre: str
    regimen_fiscal: str


@dataclass
class CfdiReceptor:
    """Datos del receptor."""
    rfc: str
    nombre: str
    domicilio_fiscal: str
    regimen_fiscal: str
    uso_cfdi: str


@dataclass
class CfdiTimbre:
    """Datos del Timbre Fiscal Digital."""
    uuid: str
    fecha_timbrado: Optional[datetime]
    rfc_prov_certif: str
    sello_cfd: str
    sello_sat: str
    no_certificado_sat: str


@dataclass
class CfdiPagoDocRelacionado:
    """Documento relacionado en un complemento de pago."""
    id_documento: str       # UUID del CFDI que se paga
    serie: str
    folio: str
    moneda_dr: str
    equivalencia_dr: float
    num_parcialidad: int
    imp_saldo_ant: float
    imp_pagado: float
    imp_saldo_insoluto: float
    objeto_imp_dr: str


@dataclass
class CfdiPago:
    """Pago individual dentro del complemento de pagos."""
    fecha_pago: Optional[datetime]
    forma_pago: str
    moneda: str
    tipo_cambio: float
    monto: float
    num_operacion: str
    rfc_emisor_cta_ord: str
    rfc_emisor_cta_ben: str
    documentos: list[CfdiPagoDocRelacionado] = field(default_factory=list)


@dataclass
class CfdiData:
    """Estructura completa de un CFDI parseado."""
    version: str
    serie: str
    folio: str
    fecha: Optional[datetime]
    forma_pago: str
    condiciones_pago: str
    subtotal: float
    descuento: float
    moneda: str
    tipo_cambio: float
    total: float
    tipo_comprobante: str  # I, E, T, N, P
    metodo_pago: str       # PUE, PPD
    lugar_expedicion: str  # CP
    exportacion: str

    emisor: Optional[CfdiEmisor]
    receptor: Optional[CfdiReceptor]
    conceptos: list[CfdiConcepto]
    timbre: Optional[CfdiTimbre]
    pagos: list[CfdiPago]

    # Totales de impuestos a nivel comprobante
    total_impuestos_trasladados: float
    total_impuestos_retenidos: float


# ============================================================================
# Parser principal
# ============================================================================
def parse_cfdi(xml_content: bytes) -> CfdiData:
    """
    Parsea un XML de CFDI y retorna un CfdiData con toda la información
    estructurada.

    Args:
        xml_content: bytes del archivo XML.

    Returns:
        CfdiData con la información completa del CFDI.

    Raises:
        etree.XMLSyntaxError: si el XML es inválido.
        ValueError: si no se puede determinar la versión del CFDI.
    """
    root = etree.fromstring(xml_content)

    # Detectar versión
    version = root.get('Version', root.get('version', ''))
    if version not in CFDI_NAMESPACES:
        raise ValueError(
            f"Versión de CFDI no soportada: '{version}'. "
            f"Soportadas: {list(CFDI_NAMESPACES.keys())}"
        )
    ns = CFDI_NAMESPACES[version]

    # --- Datos del comprobante ---
    data = CfdiData(
        version=version,
        serie=root.get('Serie', ''),
        folio=root.get('Folio', ''),
        fecha=_parse_datetime(root.get('Fecha', '')),
        forma_pago=root.get('FormaPago', ''),
        condiciones_pago=root.get('CondicionesDePago', ''),
        subtotal=_to_float(root.get('SubTotal', '0')),
        descuento=_to_float(root.get('Descuento', '0')),
        moneda=root.get('Moneda', 'MXN'),
        tipo_cambio=_to_float(root.get('TipoCambio', '1')),
        total=_to_float(root.get('Total', '0')),
        tipo_comprobante=root.get('TipoDeComprobante', ''),
        metodo_pago=root.get('MetodoPago', ''),
        lugar_expedicion=root.get('LugarExpedicion', ''),
        exportacion=root.get('Exportacion', ''),
        emisor=None,
        receptor=None,
        conceptos=[],
        timbre=None,
        pagos=[],
        total_impuestos_trasladados=0.0,
        total_impuestos_retenidos=0.0,
    )

    # --- Emisor ---
    emisor_el = root.find('cfdi:Emisor', ns)
    if emisor_el is not None:
        data.emisor = CfdiEmisor(
            rfc=emisor_el.get('Rfc', ''),
            nombre=emisor_el.get('Nombre', ''),
            regimen_fiscal=emisor_el.get('RegimenFiscal', ''),
        )

    # --- Receptor ---
    receptor_el = root.find('cfdi:Receptor', ns)
    if receptor_el is not None:
        data.receptor = CfdiReceptor(
            rfc=receptor_el.get('Rfc', ''),
            nombre=receptor_el.get('Nombre', ''),
            domicilio_fiscal=receptor_el.get('DomicilioFiscalReceptor', ''),
            regimen_fiscal=receptor_el.get('RegimenFiscalReceptor', ''),
            uso_cfdi=receptor_el.get('UsoCFDI', ''),
        )

    # --- Conceptos ---
    conceptos_el = root.find('cfdi:Conceptos', ns)
    if conceptos_el is not None:
        for concepto_el in conceptos_el.findall('cfdi:Concepto', ns):
            concepto = _parse_concepto(concepto_el, ns)
            data.conceptos.append(concepto)

    # --- Impuestos totales ---
    impuestos_el = root.find('cfdi:Impuestos', ns)
    if impuestos_el is not None:
        data.total_impuestos_trasladados = _to_float(
            impuestos_el.get('TotalImpuestosTrasladados', '0')
        )
        data.total_impuestos_retenidos = _to_float(
            impuestos_el.get('TotalImpuestosRetenidos', '0')
        )

    # --- Complemento ---
    complemento_el = root.find('cfdi:Complemento', ns)
    if complemento_el is not None:
        # Timbre Fiscal Digital
        tfd_el = complemento_el.find('tfd:TimbreFiscalDigital', ns)
        if tfd_el is not None:
            data.timbre = CfdiTimbre(
                uuid=(tfd_el.get('UUID', '') or '').upper(),
                fecha_timbrado=_parse_datetime(
                    tfd_el.get('FechaTimbrado', '')
                ),
                rfc_prov_certif=tfd_el.get('RfcProvCertif', ''),
                sello_cfd=tfd_el.get('SelloCFD', '')[:20] + '...',
                sello_sat=tfd_el.get('SelloSAT', '')[:20] + '...',
                no_certificado_sat=tfd_el.get('NoCertificadoSAT', ''),
            )

        # Complemento de Pagos 2.0
        pago_key = 'pago20' if version == '4.0' else 'pago10'
        if pago_key in ns:
            pagos_el = complemento_el.find(f'{pago_key}:Pagos', ns)
            if pagos_el is not None:
                data.pagos = _parse_pagos(pagos_el, ns, pago_key)

    return data


# ============================================================================
# Parsers internos
# ============================================================================

def _parse_concepto(concepto_el, ns: dict) -> CfdiConcepto:
    """Parsea un nodo <cfdi:Concepto> incluyendo sus impuestos."""
    concepto = CfdiConcepto(
        clave_prod_serv=concepto_el.get('ClaveProdServ', ''),
        clave_unidad=concepto_el.get('ClaveUnidad', ''),
        no_identificacion=concepto_el.get('NoIdentificacion', ''),
        cantidad=_to_float(concepto_el.get('Cantidad', '0')),
        unidad=concepto_el.get('Unidad', ''),
        descripcion=concepto_el.get('Descripcion', ''),
        valor_unitario=_to_float(concepto_el.get('ValorUnitario', '0')),
        importe=_to_float(concepto_el.get('Importe', '0')),
        descuento=_to_float(concepto_el.get('Descuento', '0')),
        objeto_imp=concepto_el.get('ObjetoImp', ''),
    )

    # Impuestos del concepto
    impuestos_el = concepto_el.find('cfdi:Impuestos', ns)
    if impuestos_el is not None:
        # Traslados
        traslados_el = impuestos_el.find('cfdi:Traslados', ns)
        if traslados_el is not None:
            for t in traslados_el.findall('cfdi:Traslado', ns):
                concepto.taxes.append(CfdiTax(
                    tax_type='traslado',
                    impuesto=t.get('Impuesto', ''),
                    impuesto_name=SAT_TAX_MAP.get(
                        t.get('Impuesto', ''), t.get('Impuesto', '')
                    ),
                    tipo_factor=t.get('TipoFactor', ''),
                    tasa_o_cuota=_to_float(t.get('TasaOCuota', '0')),
                    importe=_to_float(t.get('Importe', '0')),
                    base=_to_float(t.get('Base', '0')),
                ))

        # Retenciones
        retenciones_el = impuestos_el.find('cfdi:Retenciones', ns)
        if retenciones_el is not None:
            for r in retenciones_el.findall('cfdi:Retencion', ns):
                concepto.taxes.append(CfdiTax(
                    tax_type='retencion',
                    impuesto=r.get('Impuesto', ''),
                    impuesto_name=SAT_TAX_MAP.get(
                        r.get('Impuesto', ''), r.get('Impuesto', '')
                    ),
                    tipo_factor=r.get('TipoFactor', ''),
                    tasa_o_cuota=_to_float(r.get('TasaOCuota', '0')),
                    importe=_to_float(r.get('Importe', '0')),
                    base=_to_float(r.get('Base', '0')),
                ))

    return concepto


def _parse_pagos(pagos_el, ns: dict, pago_key: str) -> list[CfdiPago]:
    """Parsea el complemento de pagos (1.0 y 2.0)."""
    pagos = []
    for pago_el in pagos_el.findall(f'{pago_key}:Pago', ns):
        pago = CfdiPago(
            fecha_pago=_parse_datetime(pago_el.get('FechaPago', '')),
            forma_pago=pago_el.get('FormaDePagoP', ''),
            moneda=pago_el.get('MonedaP', 'MXN'),
            tipo_cambio=_to_float(pago_el.get('TipoCambioP', '1')),
            monto=_to_float(pago_el.get('Monto', '0')),
            num_operacion=pago_el.get('NumOperacion', ''),
            rfc_emisor_cta_ord=pago_el.get('RfcEmisorCtaOrd', ''),
            rfc_emisor_cta_ben=pago_el.get('RfcEmisorCtaBen', ''),
        )

        # Documentos relacionados
        for doc_el in pago_el.findall(
            f'{pago_key}:DoctoRelacionado', ns
        ):
            pago.documentos.append(CfdiPagoDocRelacionado(
                id_documento=(doc_el.get('IdDocumento', '') or '').upper(),
                serie=doc_el.get('Serie', ''),
                folio=doc_el.get('Folio', ''),
                moneda_dr=doc_el.get('MonedaDR', ''),
                equivalencia_dr=_to_float(
                    doc_el.get('EquivalenciaDR', '1')
                ),
                num_parcialidad=int(
                    doc_el.get('NumParcialidad', '0') or '0'
                ),
                imp_saldo_ant=_to_float(
                    doc_el.get('ImpSaldoAnt', '0')
                ),
                imp_pagado=_to_float(doc_el.get('ImpPagado', '0')),
                imp_saldo_insoluto=_to_float(
                    doc_el.get('ImpSaldoInsoluto', '0')
                ),
                objeto_imp_dr=doc_el.get('ObjetoImpDR', ''),
            ))

        pagos.append(pago)
    return pagos


# ============================================================================
# Helpers
# ============================================================================

def _to_float(value: str) -> float:
    """Convierte cadena a float de forma segura."""
    try:
        return float(value) if value else 0.0
    except (ValueError, TypeError):
        return 0.0


def _parse_datetime(value: str) -> Optional[datetime]:
    """Parsea datetime ISO del CFDI."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None
