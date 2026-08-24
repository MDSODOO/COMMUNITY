# -*- coding: utf-8 -*-
"""
Librería de bajo nivel para consumir el Web Service de Descarga Masiva del SAT.

Flujo oficial:
    1. Autenticacion  → obtener token (vigencia 5 min)
    2. SolicitaDescarga → crear petición de paquete
    3. VerificaSolicitudDescarga → comprobar estado
    4. DescargaResultado → bajar ZIP en Base64

Referencia técnica del SAT:
    https://www.sat.gob.mx/consultas/42968/consulta-la-documentacion-tecnica-
    del-servicio-web-de-descarga-masiva-de-cfdi-y-retenciones
"""
import base64
import datetime
import hashlib
import logging
import uuid
import zipfile
import io
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12
import OpenSSL.crypto
from lxml import etree
import requests

_logger = logging.getLogger(__name__)

# ============================================================================
# Constantes — URLs de producción del SAT
# ============================================================================
SAT_BASE_URL = "https://cfdidescargamasiva.clouda.sat.gob.mx"

SAT_URLS = {
    'autenticacion': f"{SAT_BASE_URL}/Autenticacion/Autenticacion.svc",
    'solicitud': f"{SAT_BASE_URL}/SolicitaDescargaService.svc",
    'verificacion': f"{SAT_BASE_URL}/VerificaSolicitudDescargaService.svc",
    'descarga': f"{SAT_BASE_URL}/DescargarSolicitudService.svc",
}

SAT_ACTIONS = {
    'autenticacion': (
        "http://DescargaMasivaTerceros.gob.mx/"
        "IAutenticacion/Autentica"
    ),
    'solicitud': (
        "http://DescargaMasivaTerceros.gob.mx/"
        "IDescargaMasivaTercerosService/SolicitaDescarga"
    ),
    'verificacion': (
        "http://DescargaMasivaTerceros.gob.mx/"
        "IDescargaMasivaTercerosService/VerificaSolicitudDescarga"
    ),
    'descarga': (
        "http://DescargaMasivaTerceros.gob.mx/"
        "IDescargaMasivaTercerosService/Descargar"
    ),
}

# Namespaces XML utilizados en los SOAP envelopes
NS = {
    's': 'http://schemas.xmlsoap.org/soap/envelope/',
    'u': (
        'http://docs.oasis-open.org/wss/2004/01/'
        'oasis-200401-wss-wssecurity-utility-1.0.xsd'
    ),
    'o': (
        'http://docs.oasis-open.org/wss/2004/01/'
        'oasis-200401-wss-wssecurity-secext-1.0.xsd'
    ),
    'des': 'http://DescargaMasivaTerceros.sat.gob.mx',
    'xd': 'http://www.w3.org/2000/09/xmldsig#',
}

# Timeout generoso para Odoo.sh pero sin bloquear indefinidamente
REQUEST_TIMEOUT = 60


# ============================================================================
# Clase FIEL — manejo de la e.firma
# ============================================================================
class FIEL:
    """Encapsula la e.firma (FIEL) del SAT: certificado .cer + llave .key."""

    def __init__(
        self,
        cer_der: bytes,
        key_der: bytes,
        password: str,
    ):
        """
        Args:
            cer_der: contenido binario del archivo .cer (DER / X.509).
            key_der: contenido binario del archivo .key (DER / PKCS#8 cifrado).
            password: contraseña de la llave privada.
        """
        self.cer_der = cer_der
        self.password = password.encode('utf-8')

        # --- Cargar certificado ---
        self.certificate = x509.load_der_x509_certificate(cer_der)
        self.cer_pem = self.certificate.public_bytes(serialization.Encoding.PEM)

        # --- Cargar llave privada ---
        self.private_key = serialization.load_der_private_key(
            key_der,
            password=self.password,
        )
        self.key_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # --- Número de certificado (20 dígitos) ---
        serial_hex = format(self.certificate.serial_number, 'x')
        # El SAT almacena el serial como pares de bytes → extraer caracteres pares
        self.serial_number = serial_hex[::2] if len(serial_hex) == 40 else serial_hex

        # --- RFC del titular (extraído del subject) ---
        subject = self.certificate.subject
        # OID 2.5.4.45 = UniqueIdentifier, contiene el RFC en FIEL del SAT
        uid_attrs = subject.get_attributes_for_oid(
            x509.oid.NameOID.X500_UNIQUE_IDENTIFIER
        )
        if uid_attrs:
            raw_uid = uid_attrs[0].value
            # El UID del SAT puede contener " / ..." al final
            self.rfc = raw_uid.split('/')[0].strip()
        else:
            # Fallback: buscar en serialNumber del subject
            sn_attrs = subject.get_attributes_for_oid(x509.oid.NameOID.SERIAL_NUMBER)
            self.rfc = sn_attrs[0].value.strip() if sn_attrs else ''

    @property
    def cer_b64(self) -> str:
        """Certificado en Base64 (sin cabeceras PEM)."""
        pem_str = self.cer_pem.decode('utf-8')
        return pem_str.replace(
            '-----BEGIN CERTIFICATE-----', ''
        ).replace(
            '-----END CERTIFICATE-----', ''
        ).replace('\n', '')

    @property
    def issuer_serial(self) -> str:
        """Número de serie del certificado como entero decimal (string)."""
        return str(self.certificate.serial_number)

    @property
    def issuer_name(self) -> str:
        """Nombre del emisor en formato RFC 2253 invertido (como lo espera SAT)."""
        parts = []
        for attr in reversed(self.certificate.issuer):
            oid_name = attr.oid.dotted_string
            friendly = {
                '2.5.4.6': 'C',
                '2.5.4.8': 'ST',
                '2.5.4.7': 'L',
                '2.5.4.10': 'O',
                '2.5.4.11': 'OU',
                '2.5.4.3': 'CN',
                '1.2.840.113549.1.9.1': 'E',
                '2.5.4.45': 'serialNumber',
                '2.5.4.5': 'serialNumber',
            }.get(oid_name, oid_name)
            parts.append(f"{friendly}={attr.value}")
        return ','.join(parts)

    def sign(self, data: bytes) -> bytes:
        """Firma digital SHA-256 con la llave privada."""
        return self.private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())

    def sign_b64(self, data: bytes) -> str:
        """Firma digital en Base64."""
        return base64.b64encode(self.sign(data)).decode('utf-8')

    def validate(self) -> dict:
        """Valida vigencia y tipo de la FIEL. Retorna dict con status."""
        now = datetime.datetime.now(datetime.timezone.utc)
        not_before = self.certificate.not_valid_before_utc
        not_after = self.certificate.not_valid_after_utc

        result = {
            'valid': True,
            'rfc': self.rfc,
            'serial': self.serial_number,
            'not_before': not_before.isoformat(),
            'not_after': not_after.isoformat(),
            'errors': [],
        }

        if now < not_before:
            result['valid'] = False
            result['errors'].append('El certificado aún no es válido.')
        if now > not_after:
            result['valid'] = False
            result['errors'].append('El certificado ha expirado.')

        # Verificar que sea FIEL y no CSD (sello digital)
        # La FIEL tiene KeyUsage con digitalSignature y nonRepudiation
        try:
            key_usage = self.certificate.extensions.get_extension_for_class(
                x509.KeyUsage
            )
            ku = key_usage.value
            if not (ku.digital_signature and ku.content_commitment):
                result['valid'] = False
                result['errors'].append(
                    'Este certificado NO es una FIEL. '
                    'Parece ser un CSD (Certificado de Sello Digital).'
                )
        except x509.ExtensionNotFound:
            result['errors'].append(
                'No se pudo verificar el tipo de certificado (KeyUsage ausente).'
            )

        return result


# ============================================================================
# Funciones de construcción de SOAP Envelopes
# ============================================================================

def _timestamp_xml() -> tuple[str, str]:
    """Genera Created/Expires para WS-Security (UTC, 5 min de vida)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(minutes=5)
    fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
    return now.strftime(fmt), expires.strftime(fmt)


def _build_auth_envelope(fiel: FIEL) -> str:
    """
    Construye el SOAP Envelope firmado para el servicio de Autenticación.

    El SAT requiere un envelope con:
    - BinarySecurityToken (el .cer en Base64)
    - Timestamp firmado con la llave privada
    - Signature (SignedInfo + SignatureValue + KeyInfo)
    """
    created, expires = _timestamp_xml()
    uuid_token = f"uuid-{uuid.uuid4()}-1"

    # --- Construir el Timestamp a firmar ---
    timestamp_xml = (
        f'<u:Timestamp xmlns:u="{NS["u"]}" u:Id="_0">'
        f'<u:Created>{created}</u:Created>'
        f'<u:Expires>{expires}</u:Expires>'
        f'</u:Timestamp>'
    )

    # --- Canonicalizar y firmar ---
    timestamp_element = etree.fromstring(timestamp_xml.encode('utf-8'))
    c14n = etree.tostring(timestamp_element, method='c14n', exclusive=True)
    digest_value = base64.b64encode(
        hashlib.sha1(c14n).digest()
    ).decode('utf-8')

    # --- SignedInfo (lo que se firma) ---
    signed_info_xml = (
        '<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#">'
        '<CanonicalizationMethod '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        '<SignatureMethod '
        'Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>'
        '<Reference URI="#_0">'
        '<Transforms>'
        '<Transform '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        '</Transforms>'
        '<DigestMethod '
        'Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>'
        f'<DigestValue>{digest_value}</DigestValue>'
        '</Reference>'
        '</SignedInfo>'
    )

    # Firmar el SignedInfo canonicalizado
    signed_info_el = etree.fromstring(signed_info_xml.encode('utf-8'))
    signed_info_c14n = etree.tostring(
        signed_info_el, method='c14n', exclusive=True
    )

    # Nota: SAT usa RSA-SHA1 para autenticación
    signature_value = base64.b64encode(
        fiel.private_key.sign(
            signed_info_c14n,
            padding.PKCS1v15(),
            hashes.SHA1(),  # noqa: S303 — requerido por el SAT
        )
    ).decode('utf-8')

    # --- Envelope completo ---
    envelope = f"""<s:Envelope xmlns:s="{NS['s']}" xmlns:u="{NS['u']}">
  <s:Header>
    <o:Security xmlns:o="{NS['o']}" s:mustUnderstand="1">
      <u:Timestamp u:Id="_0">
        <u:Created>{created}</u:Created>
        <u:Expires>{expires}</u:Expires>
      </u:Timestamp>
      <o:BinarySecurityToken
        u:Id="{uuid_token}"
        ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"
        EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">
        {fiel.cer_b64}
      </o:BinarySecurityToken>
      <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
        {signed_info_xml}
        <SignatureValue>{signature_value}</SignatureValue>
        <KeyInfo>
          <o:SecurityTokenReference>
            <o:Reference
              ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"
              URI="#{uuid_token}"/>
          </o:SecurityTokenReference>
        </KeyInfo>
      </Signature>
    </o:Security>
  </s:Header>
  <s:Body>
    <Autentica xmlns="http://DescargaMasivaTerceros.gob.mx"/>
  </s:Body>
</s:Envelope>"""
    return envelope


def _build_request_envelope(
    fiel: FIEL,
    token: str,
    rfc_emisor: str,
    rfc_receptor: str,
    fecha_inicio: str,
    fecha_fin: str,
    tipo_solicitud: str = 'CFDI',
    tipo_comprobante: Optional[str] = None,
) -> str:
    """
    Construye el SOAP Envelope para SolicitaDescarga.

    Args:
        token: token de autenticación obtenido previamente.
        rfc_emisor: RFC del emisor (para recibidos = RFC solicitante).
        rfc_receptor: RFC del receptor (para emitidos = RFC solicitante).
        fecha_inicio: 'YYYY-MM-DDT00:00:00' inicio del rango.
        fecha_fin: 'YYYY-MM-DDT23:59:59' fin del rango.
        tipo_solicitud: 'CFDI' o 'Metadata'.
        tipo_comprobante: 'I'=Ingreso, 'E'=Egreso, 'T'=Traslado, 'N'=Nómina, 'P'=Pago.
    """
    # --- Construir el nodo de solicitud ---
    tipo_comp_attr = ''
    if tipo_comprobante:
        tipo_comp_attr = f' TipoComprobante="{tipo_comprobante}"'

    solicitud_xml = (
        f'<des:SolicitaDescarga xmlns:des="{NS["des"]}">'
        f'<des:solicitud '
        f'RfcEmisor="{rfc_emisor}" '
        f'RfcReceptor="{rfc_receptor}" '
        f'FechaInicial="{fecha_inicio}" '
        f'FechaFinal="{fecha_fin}" '
        f'TipoSolicitud="{tipo_solicitud}"'
        f'{tipo_comp_attr}'
        f'>'
        f'<des:RfcSolicitante>{fiel.rfc}</des:RfcSolicitante>'
        f'</des:solicitud>'
        f'</des:SolicitaDescarga>'
    )

    # Extraer solo el nodo solicitud para firmarlo
    solicitud_inner = (
        f'<des:solicitud xmlns:des="{NS["des"]}" '
        f'RfcEmisor="{rfc_emisor}" '
        f'RfcReceptor="{rfc_receptor}" '
        f'FechaInicial="{fecha_inicio}" '
        f'FechaFinal="{fecha_fin}" '
        f'TipoSolicitud="{tipo_solicitud}"'
        f'{tipo_comp_attr}'
        f'>'
        f'<des:RfcSolicitante>{fiel.rfc}</des:RfcSolicitante>'
        f'</des:solicitud>'
    )

    # Firmar
    solicitud_el = etree.fromstring(solicitud_inner.encode('utf-8'))
    solicitud_c14n = etree.tostring(
        solicitud_el, method='c14n', exclusive=True
    )
    digest = base64.b64encode(
        hashlib.sha256(solicitud_c14n).digest()
    ).decode('utf-8')

    signed_info_xml = (
        '<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#">'
        '<CanonicalizationMethod '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        '<SignatureMethod '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#WithComments"/>'
        '<Reference URI="">'
        '<Transforms>'
        '<Transform '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        '</Transforms>'
        '<DigestMethod '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        f'<DigestValue>{digest}</DigestValue>'
        '</Reference>'
        '</SignedInfo>'
    )

    signed_info_el = etree.fromstring(signed_info_xml.encode('utf-8'))
    signed_info_c14n = etree.tostring(
        signed_info_el, method='c14n', exclusive=True
    )
    signature_value = fiel.sign_b64(signed_info_c14n)

    envelope = f"""<s:Envelope xmlns:s="{NS['s']}" xmlns:des="{NS['des']}" xmlns:xd="{NS['xd']}">
  <s:Header/>
  <s:Body>
    <des:SolicitaDescarga>
      <des:solicitud
        RfcEmisor="{rfc_emisor}"
        RfcReceptor="{rfc_receptor}"
        FechaInicial="{fecha_inicio}"
        FechaFinal="{fecha_fin}"
        TipoSolicitud="{tipo_solicitud}"
        {tipo_comp_attr.strip()}>
        <des:RfcSolicitante>{fiel.rfc}</des:RfcSolicitante>
        <des:Signature xmlns:des="http://www.w3.org/2000/09/xmldsig#">
          {signed_info_xml}
          <SignatureValue xmlns="http://www.w3.org/2000/09/xmldsig#">{signature_value}</SignatureValue>
          <KeyInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
            <X509Data>
              <X509IssuerSerial>
                <X509IssuerName>{fiel.issuer_name}</X509IssuerName>
                <X509SerialNumber>{fiel.issuer_serial}</X509SerialNumber>
              </X509IssuerSerial>
              <X509Certificate>{fiel.cer_b64}</X509Certificate>
            </X509Data>
          </KeyInfo>
        </des:Signature>
      </des:solicitud>
    </des:SolicitaDescarga>
  </s:Body>
</s:Envelope>"""
    return envelope


def _build_verify_envelope(
    fiel: FIEL,
    token: str,
    request_id: str,
) -> str:
    """Construye el SOAP Envelope para VerificaSolicitudDescarga."""
    verify_inner = (
        f'<des:VerificaSolicitudDescarga xmlns:des="{NS["des"]}">'
        f'<des:solicitud '
        f'IdSolicitud="{request_id}" '
        f'RfcSolicitante="{fiel.rfc}">'
        f'<des:Signature xmlns:des="http://www.w3.org/2000/09/xmldsig#">'
    )

    # Firmar el nodo solicitud
    solicitud_to_sign = (
        f'<des:solicitud xmlns:des="{NS["des"]}" '
        f'IdSolicitud="{request_id}" '
        f'RfcSolicitante="{fiel.rfc}"/>'
    )
    sol_el = etree.fromstring(solicitud_to_sign.encode('utf-8'))
    sol_c14n = etree.tostring(sol_el, method='c14n', exclusive=True)
    digest = base64.b64encode(
        hashlib.sha256(sol_c14n).digest()
    ).decode('utf-8')

    signed_info_xml = (
        '<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#">'
        '<CanonicalizationMethod '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        '<SignatureMethod '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#WithComments"/>'
        '<Reference URI="">'
        '<Transforms>'
        '<Transform '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        '</Transforms>'
        '<DigestMethod '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        f'<DigestValue>{digest}</DigestValue>'
        '</Reference>'
        '</SignedInfo>'
    )

    signed_info_el = etree.fromstring(signed_info_xml.encode('utf-8'))
    signed_info_c14n = etree.tostring(
        signed_info_el, method='c14n', exclusive=True
    )
    signature_value = fiel.sign_b64(signed_info_c14n)

    envelope = f"""<s:Envelope xmlns:s="{NS['s']}" xmlns:des="{NS['des']}" xmlns:xd="{NS['xd']}">
  <s:Header/>
  <s:Body>
    <des:VerificaSolicitudDescarga>
      <des:solicitud
        IdSolicitud="{request_id}"
        RfcSolicitante="{fiel.rfc}">
        <des:Signature xmlns:des="http://www.w3.org/2000/09/xmldsig#">
          {signed_info_xml}
          <SignatureValue xmlns="http://www.w3.org/2000/09/xmldsig#">{signature_value}</SignatureValue>
          <KeyInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
            <X509Data>
              <X509IssuerSerial>
                <X509IssuerName>{fiel.issuer_name}</X509IssuerName>
                <X509SerialNumber>{fiel.issuer_serial}</X509SerialNumber>
              </X509IssuerSerial>
              <X509Certificate>{fiel.cer_b64}</X509Certificate>
            </X509Data>
          </KeyInfo>
        </des:Signature>
      </des:solicitud>
    </des:VerificaSolicitudDescarga>
  </s:Body>
</s:Envelope>"""
    return envelope


def _build_download_envelope(
    fiel: FIEL,
    token: str,
    package_id: str,
) -> str:
    """Construye el SOAP Envelope para DescargarSolicitud (Descarga)."""
    solicitud_to_sign = (
        f'<des:PeticionDescargaMasivaTercerosEntrada '
        f'xmlns:des="{NS["des"]}" '
        f'IdPaquete="{package_id}" '
        f'RfcSolicitante="{fiel.rfc}"/>'
    )
    sol_el = etree.fromstring(solicitud_to_sign.encode('utf-8'))
    sol_c14n = etree.tostring(sol_el, method='c14n', exclusive=True)
    digest = base64.b64encode(
        hashlib.sha256(sol_c14n).digest()
    ).decode('utf-8')

    signed_info_xml = (
        '<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#">'
        '<CanonicalizationMethod '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        '<SignatureMethod '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#WithComments"/>'
        '<Reference URI="">'
        '<Transforms>'
        '<Transform '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        '</Transforms>'
        '<DigestMethod '
        'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        f'<DigestValue>{digest}</DigestValue>'
        '</Reference>'
        '</SignedInfo>'
    )

    signed_info_el = etree.fromstring(signed_info_xml.encode('utf-8'))
    signed_info_c14n = etree.tostring(
        signed_info_el, method='c14n', exclusive=True
    )
    signature_value = fiel.sign_b64(signed_info_c14n)

    envelope = f"""<s:Envelope xmlns:s="{NS['s']}" xmlns:des="{NS['des']}" xmlns:xd="{NS['xd']}">
  <s:Header/>
  <s:Body>
    <des:PeticionDescargaMasivaTercerosEntrada
      IdPaquete="{package_id}"
      RfcSolicitante="{fiel.rfc}">
      <des:Signature xmlns:des="http://www.w3.org/2000/09/xmldsig#">
        {signed_info_xml}
        <SignatureValue xmlns="http://www.w3.org/2000/09/xmldsig#">{signature_value}</SignatureValue>
        <KeyInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
          <X509Data>
            <X509IssuerSerial>
              <X509IssuerName>{fiel.issuer_name}</X509IssuerName>
              <X509SerialNumber>{fiel.issuer_serial}</X509SerialNumber>
            </X509IssuerSerial>
            <X509Certificate>{fiel.cer_b64}</X509Certificate>
          </X509Data>
        </KeyInfo>
      </des:Signature>
    </des:PeticionDescargaMasivaTercerosEntrada>
  </s:Body>
</s:Envelope>"""
    return envelope


# ============================================================================
# Funciones de llamada al Web Service
# ============================================================================

def _soap_call(url: str, action: str, envelope: str, token: str = '') -> etree._Element:
    """Ejecuta la llamada SOAP y retorna el XML de respuesta parseado."""
    headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
        'SOAPAction': action,
    }
    if token:
        headers['Authorization'] = f'WRAP access_token="{token}"'

    _logger.info("SAT WS → %s", url)
    response = requests.post(
        url,
        data=envelope.encode('utf-8'),
        headers=headers,
        timeout=REQUEST_TIMEOUT,
        verify=True,
    )
    response.raise_for_status()
    return etree.fromstring(response.content)


def authenticate(fiel: FIEL) -> str:
    """
    Paso 1: Autenticación.

    Returns:
        Token de sesión (cadena). Vigencia de 5 minutos.

    Raises:
        RuntimeError: si no se obtiene el token.
    """
    envelope = _build_auth_envelope(fiel)
    root = _soap_call(
        SAT_URLS['autenticacion'],
        SAT_ACTIONS['autenticacion'],
        envelope,
    )

    # El token viene en: Body > AutenticaResponse > AutenticaResult
    token_nodes = root.xpath(
        '//s:Body//*[local-name()="AutenticaResponse"]'
        '/*[local-name()="AutenticaResult"]',
        namespaces={'s': NS['s']},
    )
    if not token_nodes or not token_nodes[0].text:
        raise RuntimeError(
            "No se obtuvo token de autenticación del SAT. "
            "Verifique la vigencia de la FIEL."
        )
    token = token_nodes[0].text.strip()
    _logger.info("SAT: Token de autenticación obtenido correctamente.")
    return token


def request_download(
    fiel: FIEL,
    token: str,
    fecha_inicio: str,
    fecha_fin: str,
    tipo_descarga: str = 'received',
    tipo_solicitud: str = 'CFDI',
    tipo_comprobante: Optional[str] = None,
) -> dict:
    """
    Paso 2: SolicitaDescarga.

    Args:
        tipo_descarga: 'received' (recibidos) o 'issued' (emitidos).

    Returns:
        dict con 'id_solicitud', 'cod_estatus', 'mensaje'.
    """
    if tipo_descarga == 'received':
        rfc_emisor = ''
        rfc_receptor = fiel.rfc
    else:
        rfc_emisor = fiel.rfc
        rfc_receptor = ''

    envelope = _build_request_envelope(
        fiel=fiel,
        token=token,
        rfc_emisor=rfc_emisor,
        rfc_receptor=rfc_receptor,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        tipo_solicitud=tipo_solicitud,
        tipo_comprobante=tipo_comprobante,
    )
    root = _soap_call(
        SAT_URLS['solicitud'],
        SAT_ACTIONS['solicitud'],
        envelope,
        token=token,
    )

    # Parsear respuesta
    result = root.xpath(
        '//*[local-name()="SolicitaDescargaResult"]'
    )
    if not result:
        raise RuntimeError("Respuesta inesperada del SAT en SolicitaDescarga.")

    node = result[0]
    return {
        'id_solicitud': node.get('IdSolicitud', ''),
        'cod_estatus': node.get('CodEstatus', ''),
        'mensaje': node.get('Mensaje', ''),
    }


def verify_download(fiel: FIEL, token: str, request_id: str) -> dict:
    """
    Paso 3: VerificaSolicitudDescarga.

    Returns:
        dict con 'cod_estatus', 'estado_solicitud', 'codigo_estado_solicitud',
        'numero_cfdis', 'mensaje', 'paquetes' (lista de IDs de paquetes).

    Estados de solicitud:
        1 = Aceptada
        2 = En proceso
        3 = Terminada (lista para descargar)
        4 = Error
        5 = Rechazada
        6 = Vencida
    """
    envelope = _build_verify_envelope(fiel, token, request_id)
    root = _soap_call(
        SAT_URLS['verificacion'],
        SAT_ACTIONS['verificacion'],
        envelope,
        token=token,
    )

    result = root.xpath('//*[local-name()="VerificaSolicitudDescargaResult"]')
    if not result:
        raise RuntimeError("Respuesta inesperada del SAT en VerificaSolicitudDescarga.")

    node = result[0]
    paquetes_nodes = node.xpath('.//*[local-name()="IdsPaquetes"]')
    paquetes = [p.text for p in paquetes_nodes if p.text]

    return {
        'cod_estatus': node.get('CodEstatus', ''),
        'estado_solicitud': node.get('EstadoSolicitud', ''),
        'codigo_estado_solicitud': node.get('CodigoEstadoSolicitud', ''),
        'numero_cfdis': node.get('NumeroCFDIs', '0'),
        'mensaje': node.get('Mensaje', ''),
        'paquetes': paquetes,
    }


def download_package(fiel: FIEL, token: str, package_id: str) -> bytes:
    """
    Paso 4: DescargarSolicitud.

    Returns:
        Contenido del ZIP en bytes (decodificado de Base64).
    """
    envelope = _build_download_envelope(fiel, token, package_id)
    root = _soap_call(
        SAT_URLS['descarga'],
        SAT_ACTIONS['descarga'],
        envelope,
        token=token,
    )

    # El paquete viene en Base64 dentro de <Paquete>
    paquete_nodes = root.xpath('//*[local-name()="Paquete"]')
    if not paquete_nodes or not paquete_nodes[0].text:
        raise RuntimeError(
            f"No se obtuvo el paquete {package_id} del SAT."
        )

    zip_bytes = base64.b64decode(paquete_nodes[0].text)
    _logger.info(
        "SAT: Paquete %s descargado (%d bytes).",
        package_id, len(zip_bytes),
    )
    return zip_bytes


def extract_xmls_from_zip(zip_bytes: bytes) -> list[tuple[str, bytes]]:
    """
    Extrae los archivos XML de un ZIP descargado del SAT.

    Returns:
        Lista de tuplas (nombre_archivo, contenido_xml_bytes).
    """
    xmls = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
        for name in zf.namelist():
            if name.lower().endswith('.xml'):
                xmls.append((name, zf.read(name)))
    _logger.info("SAT: %d archivos XML extraídos del ZIP.", len(xmls))
    return xmls
