/** @odoo-module */
/**
 * POS Network Error Silencer
 *
 * PROBLEMA A — Errores de red (TypeError: Failed to fetch):
 *   El POS hace checks de conectividad periódicos hacia:
 *     - /pos/ping           (proxy hardware / IoT box)
 *     - /pos/hardware_proxy (proxy hardware en redes locales)
 *     - /longpolling/       (bus de notificaciones en tiempo real)
 *   Cuando la red falla, producen en consola:
 *     • "Failed to load resource: net::ERR_*"     (pestaña Network)
 *     • "Uncaught (in promise) TypeError: Failed to fetch"  (Console)
 *
 * PROBLEMA B — ConnectionLostError por hw_proxy/display_refresh 404:
 *   El POS intenta actualizar la pantalla del cliente via:
 *     - /hw_proxy/display_refresh  (Customer Display / IoT box)
 *   Si no hay caja IoT configurada, el servidor devuelve 404 y Odoo traduce
 *   esa respuesta en un ConnectionLostError que inunda la consola.
 *   Este error NO es un fallo de red (la respuesta HTTP llegó) sino una
 *   condición esperada cuando no hay hardware de pantalla conectado.
 *
 * SOLUCIÓN:
 *   1. Interceptar window.fetch para URLs de hardware conocidas:
 *      - Fallas de red → catch silencioso que re-lanza para el PosStore.
 *      - Respuestas 404 de hw_proxy → log debug, re-lanza para PosStore.
 *   2. Escuchar 'unhandledrejection' en /pos/* y suprimir:
 *      - TypeError de red (Failed to fetch, Load failed, etc.)
 *      - ConnectionLostError de hw_proxy sin catch en Odoo core.
 *
 * SEGURIDAD:
 *   - Interceptor de fetch solo actúa sobre URLs de patrones conocidos.
 *   - unhandledrejection solo activa en pathname /pos/*.
 *   - No suprime errores de programación (ReferenceError, TypeError de null).
 *   - Siempre re-lanza para que el PosStore maneje offline/online state.
 *   - Loguea a console.debug (visible en devtools → filtro "Verbose").
 */

// ─────────────────────────────────────────────────────────────────────────────
//  Configuración
// ─────────────────────────────────────────────────────────────────────────────

/** URLs de red (substrings) cuyas fallas se suprimen del console.error. */
const _SILENT_URL_PATTERNS = [
    '/pos/ping',
    '/pos/hardware_proxy',
    '/hw_proxy/',          // Customer Display, impresoras, básculas via IoT
    '/longpolling/',
];

/**
 * URLs de hw_proxy que devuelven 404 cuando no hay IoT box configurada.
 * El fetch resuelve (no rechaza), pero Odoo lanza ConnectionLostError después.
 */
const _HW_PROXY_404_PATTERNS = [
    '/hw_proxy/display_refresh',
    '/hw_proxy/status',
    '/hw_proxy/hello',
];

/** Mensajes de TypeError de red en distintos navegadores. */
const _NETWORK_ERROR_MESSAGES = [
    'Failed to fetch',         // Chrome / Firefox
    'Load failed',             // Safari
    'NetworkError',            // Firefox en algunos casos
    'Network request failed',
];

// ─────────────────────────────────────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────────────────────────────────────

function _resolveUrl(input) {
    if (typeof input === 'string') return input;
    if (input instanceof URL)     return input.href;
    if (input && input.url)       return input.url;
    return '';
}

function _isSilentUrl(url) {
    return _SILENT_URL_PATTERNS.some((pattern) => url.includes(pattern));
}

function _isHwProxyUrl(url) {
    return _HW_PROXY_404_PATTERNS.some((pattern) => url.includes(pattern));
}

/** TypeError de falla de red (sin respuesta HTTP). */
function _isNetworkTypeError(reason) {
    if (!(reason instanceof TypeError)) return false;
    const msg = (reason.message || '').toString();
    return _NETWORK_ERROR_MESSAGES.some((m) => msg.includes(m));
}

/**
 * ConnectionLostError que Odoo genera cuando hw_proxy devuelve 404.
 * Odoo lo lanza como Error con nombre 'ConnectionLostError' o con un
 * message que contiene el endpoint.
 */
function _isHwProxyConnectionLost(reason) {
    if (!reason) return false;
    const name = reason.name || (reason.constructor && reason.constructor.name) || '';
    const msg  = (reason.message || '').toString();
    return (
        name === 'ConnectionLostError' ||
        msg.includes('hw_proxy') ||
        msg.includes('display_refresh') ||
        msg.includes('ConnectionLostError')
    );
}

// ─────────────────────────────────────────────────────────────────────────────
//  1. Fetch interceptor
//     - Fallas de red en URLs silenciadas → debug + re-lanza
//     - Respuestas 404 de hw_proxy       → debug, devuelve respuesta (no re-lanza)
// ─────────────────────────────────────────────────────────────────────────────

const _nativeFetch = window.fetch;

window.fetch = function biPosSilentFetch(input, init) {
    const url = _resolveUrl(input);
    if (!_isSilentUrl(url)) {
        return _nativeFetch.call(this, input, init);
    }

    const shortUrl = url.split('?')[0];

    return _nativeFetch.call(this, input, init)
        .then((response) => {
            // Para hw_proxy: si el servidor devuelve 404, significa que no hay
            // IoT box configurada. Logeamos a debug pero NO alteramos la Response
            // para que el PosStore pueda detectarlo y cambiar de estado.
            if (!response.ok && _isHwProxyUrl(url)) {
                console.debug(
                    '[bi_pos_stock] hw_proxy endpoint not found — IoT box not configured:',
                    shortUrl, response.status,
                );
            }
            return response;
        })
        .catch((err) => {
            // Falla de red: el servidor no es alcanzable (offline, DNS, timeout).
            console.debug(
                '[bi_pos_stock] POS hardware connectivity failed (expected when offline):',
                shortUrl, err?.message,
            );
            // Re-lanza: el PosStore necesita el rechazo para activar modo offline.
            throw err;
        });
};

// ─────────────────────────────────────────────────────────────────────────────
//  2. Unhandled rejection handler
//     Suprime errores de red y ConnectionLostError sin catch en /pos/*
// ─────────────────────────────────────────────────────────────────────────────

if (window.location.pathname.startsWith('/pos/')) {
    window.addEventListener('unhandledrejection', (event) => {
        const isSuppressible = (
            _isNetworkTypeError(event.reason) ||
            _isHwProxyConnectionLost(event.reason)
        );
        if (isSuppressible) {
            // preventDefault() evita "Uncaught (in promise)" en la consola.
            event.preventDefault();
            console.debug(
                '[bi_pos_stock] POS hardware/network rejection suppressed:',
                event.reason?.name || event.reason?.message,
            );
        }
    }, { passive: true });
}
