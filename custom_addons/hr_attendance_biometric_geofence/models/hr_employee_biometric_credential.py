import base64
import hashlib
import io
import json
import logging

import cbor2
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

COSE_ALG_ES256 = -7
COSE_ALG_RS256 = -257


def _b64url_decode(data):
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


class HrEmployeeBiometricCredential(models.Model):
    _name = "hr.employee.biometric.credential"
    _description = "Credencial biométrica (WebAuthn/FIDO2) de un empleado"
    _rec_name = "name"

    name = fields.Char(
        string="Nombre del dispositivo", required=True,
        help="Ej. 'Huella - laptop de Daniel' o 'Llave USB recepción Mérida'.")
    employee_id = fields.Many2one(
        "hr.employee", string="Empleado", required=True, index=True, ondelete="cascade")
    credential_id = fields.Char(string="Credential ID (WebAuthn)", required=True, index=True)
    public_key = fields.Text(string="Clave pública (COSE, base64)", required=True)
    algorithm = fields.Selection(
        [("ES256", "ES256 (EC P-256)"), ("RS256", "RS256 (RSA)")], required=True)
    sign_count = fields.Integer(string="Contador de firmas", default=0)
    active = fields.Boolean(string="Activo", default=True)
    last_used = fields.Datetime(string="Último uso", readonly=True)

    _credential_id_unique = models.Constraint(
        "unique(credential_id)",
        "Esta credencial ya está registrada.",
    )

    @api.model
    def _register_from_attestation(self, employee, name, credential_id_b64url, attestation_object_b64,
                                    client_data_json_b64, expected_challenge, expected_origin, expected_rp_id):
        """Alta de una credencial a partir de navigator.credentials.create().
        No se valida la cadena de atestiguación del fabricante -- esto es
        control de acceso interno, no verificación de proveedor de
        hardware -- solo se extrae la clave pública del authenticatorData,
        que es lo único necesario para verificar firmas futuras.
        """
        client_data = json.loads(_b64url_decode(client_data_json_b64))
        if client_data.get("type") != "webauthn.create":
            raise ValidationError("Tipo de respuesta de registro inesperado.")
        if client_data.get("challenge") != expected_challenge:
            raise ValidationError("El desafío (challenge) de registro no coincide.")
        if client_data.get("origin") != expected_origin:
            raise ValidationError("Origen no autorizado para el registro de la credencial.")

        attestation_object = cbor2.loads(_b64url_decode(attestation_object_b64))
        auth_data = attestation_object["authData"]

        rp_id_hash = hashlib.sha256(expected_rp_id.encode()).digest()
        if auth_data[:32] != rp_id_hash:
            raise ValidationError("El registro no corresponde a este sitio (rpIdHash no coincide).")

        cose_key = self._parse_credential_public_key(auth_data)
        algorithm = self._algorithm_from_cose_key(cose_key)

        return self.create({
            "name": name,
            "employee_id": employee.id,
            "credential_id": credential_id_b64url,
            "public_key": base64.b64encode(cbor2.dumps(cose_key)).decode(),
            "algorithm": algorithm,
            "sign_count": 0,
        })

    @staticmethod
    def _parse_credential_public_key(auth_data):
        # rpIdHash(32) + flags(1) + signCount(4) = 37 bytes de cabecera fija,
        # luego AAGUID(16) + credentialIdLength(2) + credentialId(N) + clave COSE.
        if len(auth_data) < 37:
            raise ValidationError("authenticatorData inválido (demasiado corto).")
        flags = auth_data[32]
        if not (flags & 0x40):
            raise ValidationError("El autenticador no envió datos de credencial (AT flag ausente).")
        pos = 37 + 16
        cred_id_len = int.from_bytes(auth_data[pos:pos + 2], "big")
        pos += 2 + cred_id_len
        decoder = cbor2.CBORDecoder(io.BytesIO(auth_data[pos:]))
        return decoder.decode()

    @staticmethod
    def _algorithm_from_cose_key(cose_key):
        alg = cose_key.get(3)
        if alg == COSE_ALG_ES256:
            return "ES256"
        if alg == COSE_ALG_RS256:
            return "RS256"
        raise ValidationError("Algoritmo de credencial no soportado (solo ES256/RS256).")

    def _load_public_key(self):
        self.ensure_one()
        cose_key = cbor2.loads(base64.b64decode(self.public_key))
        if self.algorithm == "ES256":
            x = cose_key[-2]
            y = cose_key[-3]
            numbers = ec.EllipticCurvePublicNumbers(
                int.from_bytes(x, "big"), int.from_bytes(y, "big"), ec.SECP256R1())
            return numbers.public_key()
        n = int.from_bytes(cose_key[-1], "big")
        e = int.from_bytes(cose_key[-2], "big")
        return rsa.RSAPublicNumbers(e, n).public_key()

    def _verify_and_consume(self, client_data_json_b64, authenticator_data_b64, signature_b64,
                             expected_challenge, expected_origin, expected_rp_id):
        """Verifica la firma WebAuthn de un intento de check-in/out y
        actualiza el contador anti-repetición. Lanza ValidationError si
        algo no cuadra -- nunca se asume válido por omisión.
        """
        self.ensure_one()
        client_data_json = _b64url_decode(client_data_json_b64)
        authenticator_data = _b64url_decode(authenticator_data_b64)
        signature = _b64url_decode(signature_b64)

        client_data = json.loads(client_data_json)
        if client_data.get("type") != "webauthn.get":
            raise ValidationError("Tipo de respuesta biométrica inesperado.")
        if client_data.get("challenge") != expected_challenge:
            raise ValidationError("El desafío (challenge) no coincide -- posible repetición.")
        if client_data.get("origin") != expected_origin:
            raise ValidationError("Origen no autorizado para esta credencial.")

        rp_id_hash = hashlib.sha256(expected_rp_id.encode()).digest()
        if authenticator_data[:32] != rp_id_hash:
            raise ValidationError("La credencial no corresponde a este sitio (rpIdHash no coincide).")

        flags = authenticator_data[32]
        if not (flags & 0x01):
            raise ValidationError("El autenticador no confirmó presencia del usuario.")

        signed_data = authenticator_data + hashlib.sha256(client_data_json).digest()
        public_key = self._load_public_key()
        try:
            if self.algorithm == "ES256":
                public_key.verify(signature, signed_data, ec.ECDSA(hashes.SHA256()))
            else:
                public_key.verify(signature, signed_data, padding.PKCS1v15(), hashes.SHA256())
        except InvalidSignature as exc:
            raise ValidationError("La firma biométrica no es válida.") from exc

        new_sign_count = int.from_bytes(authenticator_data[33:37], "big")
        if new_sign_count != 0 and self.sign_count != 0 and new_sign_count <= self.sign_count:
            _logger.warning(
                "Posible clonación de credencial biométrica #%s (empleado %s): "
                "sign_count no incrementó (almacenado=%s, recibido=%s).",
                self.id, self.employee_id.name, self.sign_count, new_sign_count,
            )
            raise ValidationError(
                "El contador de la credencial no incrementó -- posible clonación. Contacta a RRHH.")

        self.sudo().write({"sign_count": new_sign_count, "last_used": fields.Datetime.now()})
