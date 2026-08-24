import base64
import logging
import os

from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

CHALLENGE_SESSION_KEY = "hr_attendance_biometric_challenge"


def _new_challenge():
    return base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")


def _rp_id_and_origin():
    rp_id = request.httprequest.host.split(":")[0]
    origin = request.httprequest.host_url.rstrip("/")
    return rp_id, origin


class HrAttendanceBiometricController(http.Controller):
    """Endpoints para el check-in "fuerte" (huella + ubicación), separados
    a propósito del flujo pasivo de hr_attendance_ip_autologin (login/logout)
    y del kiosco/systray de hr_attendance -- ninguno de los dos se modifica.
    """

    @http.route("/hr_attendance_biometric/enroll_options", type="jsonrpc", auth="user")
    def enroll_options(self):
        employee = request.env.user.employee_id
        if not employee:
            raise ValidationError(_("Tu usuario no tiene un empleado asociado en esta compañía."))
        rp_id, _origin = _rp_id_and_origin()
        challenge = _new_challenge()
        request.session[CHALLENGE_SESSION_KEY] = challenge
        existing = employee.biometric_credential_ids.filtered("active").mapped("credential_id")
        return {
            "rp": {"id": rp_id, "name": "MedicineDepot Sureste - Asistencias"},
            "user": {
                "id": base64.urlsafe_b64encode(str(employee.id).encode()).decode().rstrip("="),
                "name": employee.user_id.login or employee.name,
                "displayName": employee.name,
            },
            "challenge": challenge,
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},
                {"type": "public-key", "alg": -257},
            ],
            "excludeCredentials": [{"type": "public-key", "id": cred_id} for cred_id in existing],
            "authenticatorSelection": {"userVerification": "required"},
            "attestation": "none",
            "timeout": 60000,
        }

    @http.route("/hr_attendance_biometric/enroll", type="jsonrpc", auth="user")
    def enroll(self, name, credential_id, attestation_object, client_data_json):
        employee = request.env.user.employee_id
        if not employee:
            raise ValidationError(_("Tu usuario no tiene un empleado asociado en esta compañía."))
        challenge = request.session.get(CHALLENGE_SESSION_KEY)
        if not challenge:
            raise ValidationError(_("El desafío de registro expiró, intenta de nuevo."))
        rp_id, origin = _rp_id_and_origin()
        credential = request.env["hr.employee.biometric.credential"].sudo()._register_from_attestation(
            employee, name or _("Dispositivo sin nombre"), credential_id, attestation_object, client_data_json,
            expected_challenge=challenge, expected_origin=origin, expected_rp_id=rp_id,
        )
        request.session.pop(CHALLENGE_SESSION_KEY, None)
        _logger.info(
            "hr_attendance_biometric_geofence: credencial #%s registrada para %s",
            credential.id, employee.name,
        )
        return {"status": "success", "id": credential.id, "name": credential.name}

    @http.route("/hr_attendance_biometric/checkin_options", type="jsonrpc", auth="user")
    def checkin_options(self):
        employee = request.env.user.employee_id
        if not employee:
            raise ValidationError(_("Tu usuario no tiene un empleado asociado en esta compañía."))
        credentials = employee.biometric_credential_ids.filtered("active")
        if not credentials:
            return {"error": "no_credential"}
        rp_id, _origin = _rp_id_and_origin()
        challenge = _new_challenge()
        request.session[CHALLENGE_SESSION_KEY] = challenge
        return {
            "rpId": rp_id,
            "challenge": challenge,
            "timeout": 60000,
            "userVerification": "required",
            "allowCredentials": [{"type": "public-key", "id": c.credential_id} for c in credentials],
        }

    @http.route("/hr_attendance_biometric/checkin", type="jsonrpc", auth="user")
    def checkin(self, credential_id, client_data_json, authenticator_data, signature,
                latitude=None, longitude=None):
        employee = request.env.user.employee_id
        if not employee:
            raise ValidationError(_("Tu usuario no tiene un empleado asociado en esta compañía."))

        challenge = request.session.get(CHALLENGE_SESSION_KEY)
        if not challenge:
            raise ValidationError(_("El desafío de verificación expiró, intenta de nuevo."))

        credential = employee.biometric_credential_ids.filtered(
            lambda c: c.active and c.credential_id == credential_id
        )
        if not credential:
            raise ValidationError(_("Esta credencial no pertenece a tu usuario."))

        rp_id, origin = _rp_id_and_origin()
        # Verifica firma + challenge + origin + rpIdHash + contador
        # anti-repetición. Lanza ValidationError si algo no cuadra --
        # nunca se llega a _attendance_action_change sin esto.
        credential._verify_and_consume(
            client_data_json, authenticator_data, signature,
            expected_challenge=challenge, expected_origin=origin, expected_rp_id=rp_id,
        )
        request.session.pop(CHALLENGE_SESSION_KEY, None)

        # --- Ubicación: IP de sucursal (prioritaria, ya auditada) primero,
        # geocerca GPS como respaldo solo si la IP no coincide. ---
        remote_ip = request.httprequest.remote_addr
        authorized_ips = employee.company_id.attendance_authorized_ip_ids.filtered("active")
        ip_match = any(rec._matches(remote_ip) for rec in authorized_ips)

        geofence = request.env["hr.attendance.geofence"]
        location_source = "manual"
        if ip_match:
            location_source = "ip"
        elif latitude and longitude:
            try:
                geofence = geofence.sudo()._find_matching(
                    employee.company_id, float(latitude), float(longitude))
            except (TypeError, ValueError):
                geofence = geofence.browse()
            if geofence:
                location_source = "geofence"

        # Los nombres de estas claves se anteponen con in_/out_ dentro de
        # _attendance_action_change (core) -- deben coincidir exactamente
        # con los campos in_*/out_* añadidos en models/hr_attendance.py.
        geo_information = {
            "mode": "biometric",
            "ip_address": remote_ip,
            "browser": request.httprequest.user_agent.browser,
            "biometric_verified": True,
            "biometric_credential_id": credential.id,
            "location_source": location_source,
            "geofence_id": geofence.id,
        }
        if latitude and longitude:
            geo_information["latitude"] = float(latitude)
            geo_information["longitude"] = float(longitude)
            geo_information["location"] = "%s, %s" % (latitude, longitude)
        elif location_source == "ip":
            geo_information["location"] = _("Red autorizada de sucursal (%s)") % employee.company_id.name

        attendance = employee._attendance_action_change(geo_information)

        if location_source == "manual":
            attendance.sudo().message_post(body=_(
                "Check-in/out con huella verificada, pero SIN coincidencia de IP de "
                "sucursal ni geocerca autorizada. Requiere revisión de RRHH."
            ))
            _logger.warning(
                "hr_attendance_biometric_geofence: asistencia #%s de %s sin "
                "validación de ubicación (IP ni geocerca).", attendance.id, employee.name,
            )

        return {
            "status": "success",
            "attendance_id": attendance.id,
            "check_out": bool(attendance.check_out),
            "location_source": location_source,
        }
