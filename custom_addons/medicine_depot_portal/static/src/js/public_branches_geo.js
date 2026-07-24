/** @odoo-module **/
// Medicine Depot · Branches geolocation + QR code generator
// Geolocation API with permission handling, timeout, fallback.
// QR generation with resilient external fallback.

// ── Geolocation ───────────────────────────────────────────────────────────────
const GEO_CACHE_KEY = 'md_geo_position';
const GEO_CACHE_TTL = 10 * 60 * 1000; // 10 min

function readCachedPosition() {
    try {
        const raw = sessionStorage.getItem(GEO_CACHE_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        if (!parsed || (Date.now() - parsed.ts) > GEO_CACHE_TTL) {
            sessionStorage.removeItem(GEO_CACHE_KEY);
            return null;
        }
        return parsed;
    } catch {
        return null;
    }
}

function writeCachedPosition(lat, lng) {
    try {
        sessionStorage.setItem(GEO_CACHE_KEY, JSON.stringify({ lat, lng, ts: Date.now() }));
    } catch {
        // sessionStorage no disponible (modo privado / cuota): se ignora.
    }
}

function initGeolocation() {
    const btn = document.querySelector('[data-md-geolocate]');
    if (!btn || !navigator.geolocation) {
        btn?.setAttribute('disabled', '');
        btn?.setAttribute('title', 'Geolocalización no disponible en este navegador');
        return;
    }

    btn.addEventListener('click', () => {
        // Reutiliza la última posición cacheada para evitar pedir permiso/red de nuevo.
        const cached = readCachedPosition();
        if (cached) {
            onGeoSuccess(cached.lat, cached.lng);
            return;
        }

        btn.classList.add('is-loading');
        btn.setAttribute('aria-busy', 'true');

        const timeoutId = setTimeout(() => {
            btn.classList.remove('is-loading');
            btn.removeAttribute('aria-busy');
            showGeoError('timeout');
        }, 5000);

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                clearTimeout(timeoutId);
                btn.classList.remove('is-loading');
                btn.removeAttribute('aria-busy');
                writeCachedPosition(pos.coords.latitude, pos.coords.longitude);
                onGeoSuccess(pos.coords.latitude, pos.coords.longitude);
            },
            (err) => {
                clearTimeout(timeoutId);
                btn.classList.remove('is-loading');
                btn.removeAttribute('aria-busy');
                showGeoError(err.code);
            },
            { timeout: 4500, maximumAge: 60000 }
        );
    });
}

function onGeoSuccess(lat, lng) {
    // Dispatch event for the branches snippet to react
    const root = document.querySelector('.s_md_branches');
    if (root) {
        root.dispatchEvent(new CustomEvent('md:branches:user-location', {
            bubbles: true,
            detail: { lat, lng },
        }));
    }

    // Update user pin in fallback SVG if present
    const svg = document.querySelector('.md-peninsula-svg');
    if (svg) {
        const existing = svg.querySelector('.md-user-pin');
        if (existing) existing.remove();

        // Rough Yucatan Peninsula bounds for relative SVG positioning
        const bounds = { latMin: 17.5, latMax: 21.8, lngMin: -91.5, lngMax: -86.5 };
        const svgW = 800, svgH = 560;
        const x = Math.max(0, Math.min(svgW, ((lng - bounds.lngMin) / (bounds.lngMax - bounds.lngMin)) * svgW));
        const y = Math.max(0, Math.min(svgH, svgH - ((lat - bounds.latMin) / (bounds.latMax - bounds.latMin)) * svgH));

        const pin = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        pin.setAttribute('class', 'md-user-pin');
        pin.setAttribute('cx', x.toFixed(1));
        pin.setAttribute('cy', y.toFixed(1));
        pin.setAttribute('r', '10');
        pin.setAttribute('fill', '#16A6D9');
        pin.setAttribute('stroke', '#fff');
        pin.setAttribute('stroke-width', '2');
        pin.setAttribute('aria-label', 'Tu ubicación');
        svg.appendChild(pin);
    }
}

function showGeoError(code) {
    const msgEl = document.querySelector('[data-md-geo-error]');
    if (!msgEl) return;

    const messages = {
        1: 'Permiso denegado. Actívalo en la configuración de tu navegador.',
        2: 'No se pudo determinar tu ubicación. Intenta de nuevo.',
        3: 'Tiempo de espera agotado. Intenta de nuevo.',
        timeout: 'Tiempo de espera agotado. Intenta de nuevo.',
    };

    msgEl.textContent = messages[code] || 'Error de geolocalización.';
    msgEl.removeAttribute('hidden');
    setTimeout(() => msgEl.setAttribute('hidden', ''), 5000);
}

// ── Static SVG pin interactions (a11y + keyboard) ────────────────────────────
function initStaticPinInteractions() {
    const root = document.querySelector('.s_md_branches');
    if (!root) return;

    const pins = root.querySelectorAll('.md-dna-pin[data-pin-city]');
    if (!pins.length) return;

    function selectPin(pin) {
        pins.forEach((node) => node.classList.remove('is-active'));
        pin.classList.add('is-active');

        const city = pin.dataset.pinCity || '';
        const state = pin.dataset.pinState || '';

        root.dispatchEvent(new CustomEvent('md:branches:card-focus', {
            bubbles: true,
            detail: { city, state },
        }));
        root.dispatchEvent(new CustomEvent('md:branches:state-change', {
            bubbles: true,
            detail: { state: state || 'all' },
        }));
    }

    pins.forEach((pin) => {
        pin.addEventListener('click', () => selectPin(pin));
        pin.addEventListener('keydown', (ev) => {
            if (ev.key !== 'Enter' && ev.key !== ' ') return;
            ev.preventDefault();
            selectPin(pin);
        });
    });
}

// ── QR Code generator ─────────────────────────────────────────────────────────
function generateQR(url, size = 96) {
    const encoded = encodeURIComponent(url);
    return `/report/barcode/QR/${encoded}?width=${size}&height=${size}`;
}

function appendQRFallbackLink(container, url) {
    const link = document.createElement('a');
    link.href = url;
    link.textContent = 'Ver en Maps →';
    link.className = 'md-btn md-btn--ghost';
    link.target = '_blank';
    link.rel = 'noopener';
    container.appendChild(link);

    const label = document.createElement('span');
    label.textContent = 'Enlace directo';
    container.appendChild(label);
}

function initQRCodes() {
    document.querySelectorAll('[data-md-qr]').forEach((container) => {
        const url = container.dataset.mdQr;
        const size = parseInt(container.dataset.mdQrSize || '96', 10);
        if (!url) return;

        container.innerHTML = '';
        const img = document.createElement('img');
        img.src = generateQR(url, size);
        img.width = size;
        img.height = size;
        img.alt = `Código QR: ${url}`;
        img.loading = 'lazy';
        img.className = 'md-qr-code';
        img.addEventListener('error', () => {
            container.innerHTML = '';
            appendQRFallbackLink(container, url);
        }, { once: true });
        container.appendChild(img);

        const label = document.createElement('span');
        label.textContent = 'Escanea para llegar';
        container.appendChild(label);
    });
}

// ── Init ──────────────────────────────────────────────────────────────────────
// Odoo 19 carga los assets de forma diferida/asíncrona: para cuando este script
// se evalúa, el DOM puede estar ya 'interactive'/'complete' y DOMContentLoaded
// no volverá a dispararse. Evaluamos readyState y arrancamos de inmediato si ya
// está listo, evitando que geolocalización, pines y QRs queden sin inicializar.
//
// Guard: document.body puede ser null si este script se evalúa dentro del
// iframe transitorio del WebsiteBuilder (onIframeLoad). Salimos limpiamente.
function initBranchesGeo() {
    if (!document.body) return; // iframe transitorio del WebsiteBuilder
    initGeolocation();
    initStaticPinInteractions();
    initQRCodes();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBranchesGeo, { once: true });
} else {
    initBranchesGeo();
}
