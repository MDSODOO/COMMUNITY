/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

function b64urlToBuffer(b64url) {
    const pad = "=".repeat((4 - (b64url.length % 4)) % 4);
    const base64 = (b64url + pad).replace(/-/g, "+").replace(/_/g, "/");
    const raw = window.atob(base64);
    const buffer = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) {
        buffer[i] = raw.charCodeAt(i);
    }
    return buffer.buffer;
}

function bufferToB64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let str = "";
    for (const b of bytes) {
        str += String.fromCharCode(b);
    }
    return window.btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export class BiometricAttendance extends Component {
    static template = "hr_attendance_biometric_geofence.CheckinAction";
    static props = ["*"];

    setup() {
        this.notification = useService("notification");
        this.state = useState({ busy: false });
    }

    get webauthnSupported() {
        return !!(window.PublicKeyCredential && navigator.credentials);
    }

    async _getPosition() {
        if (!navigator.geolocation) {
            return {};
        }
        try {
            const position = await new Promise((resolve, reject) =>
                navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 })
            );
            return { latitude: position.coords.latitude, longitude: position.coords.longitude };
        } catch {
            // Sin GPS disponible/autorizado: se sigue intentando el
            // check-in, la validación por IP de sucursal puede bastar.
            return {};
        }
    }

    async onEnroll() {
        if (!this.webauthnSupported) {
            this.notification.add(
                "Este navegador/dispositivo no soporta WebAuthn (huella/llave de seguridad).",
                { type: "danger" }
            );
            return;
        }
        this.state.busy = true;
        try {
            const options = await rpc("/hr_attendance_biometric/enroll_options", {});
            const publicKey = {
                ...options,
                challenge: b64urlToBuffer(options.challenge),
                user: { ...options.user, id: b64urlToBuffer(options.user.id) },
                excludeCredentials: (options.excludeCredentials || []).map((c) => ({
                    ...c,
                    id: b64urlToBuffer(c.id),
                })),
            };
            const credential = await navigator.credentials.create({ publicKey });
            const response = credential.response;
            const deviceName = window.prompt("Nombre para este dispositivo", "Mi huella") || "Dispositivo";
            await rpc("/hr_attendance_biometric/enroll", {
                name: deviceName,
                credential_id: bufferToB64url(credential.rawId),
                attestation_object: bufferToB64url(response.attestationObject),
                client_data_json: bufferToB64url(response.clientDataJSON),
            });
            this.notification.add("Huella registrada correctamente.", { type: "success" });
        } catch (error) {
            this.notification.add(this._errorMessage(error), { type: "danger" });
        } finally {
            this.state.busy = false;
        }
    }

    async onCheckin() {
        if (!this.webauthnSupported) {
            this.notification.add(
                "Este navegador/dispositivo no soporta WebAuthn (huella/llave de seguridad).",
                { type: "danger" }
            );
            return;
        }
        this.state.busy = true;
        try {
            const options = await rpc("/hr_attendance_biometric/checkin_options", {});
            if (options.error === "no_credential") {
                this.notification.add(
                    "No tienes una huella registrada todavía. Regístrala primero.",
                    { type: "warning" }
                );
                return;
            }
            const publicKey = {
                ...options,
                challenge: b64urlToBuffer(options.challenge),
                allowCredentials: (options.allowCredentials || []).map((c) => ({
                    ...c,
                    id: b64urlToBuffer(c.id),
                })),
            };
            const assertion = await navigator.credentials.get({ publicKey });
            const response = assertion.response;
            const position = await this._getPosition();
            const result = await rpc("/hr_attendance_biometric/checkin", {
                credential_id: bufferToB64url(assertion.rawId),
                client_data_json: bufferToB64url(response.clientDataJSON),
                authenticator_data: bufferToB64url(response.authenticatorData),
                signature: bufferToB64url(response.signature),
                latitude: position.latitude,
                longitude: position.longitude,
            });
            const locationLabel = {
                ip: "red de sucursal",
                geofence: "geocerca GPS",
                manual: "sin validar -- quedó marcada para revisión de RRHH",
            }[result.location_source];
            this.notification.add(
                (result.check_out ? "Salida registrada. " : "Entrada registrada. ") +
                    `Ubicación: ${locationLabel}.`,
                { type: result.location_source === "manual" ? "warning" : "success" }
            );
        } catch (error) {
            this.notification.add(this._errorMessage(error), { type: "danger" });
        } finally {
            this.state.busy = false;
        }
    }

    _errorMessage(error) {
        if (error && error.name === "NotAllowedError") {
            return "La verificación biométrica fue cancelada o el lector no respondió.";
        }
        return (
            (error && error.data && error.data.message) ||
            (error && error.message) ||
            "No se pudo completar la operación."
        );
    }
}

registry.category("actions").add("hr_attendance_biometric_geofence.checkin_action", BiometricAttendance);
