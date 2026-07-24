/** @odoo-module **/
// Medicine Depot · Google Maps integration — Fase 4
// Loads Google Maps API lazily, renders AdvancedMarkerElement with animated
// DNA SVG pins. Falls back to the static SVG peninsula if API is unavailable.

import publicWidget from '@web/legacy/js/public/public_widget';

function _esc(str) {
    const d = document.createElement('span');
    d.textContent = str || '';
    return d.innerHTML;
}

// ── API Loader (singleton promise, safe against double injection) ─────────────
let _mapsApiPromise = null;
let _markerClustererPromise = null;
let _leafletPromise = null;

function loadGoogleMapsAPI(apiKey) {
    if (_mapsApiPromise) return _mapsApiPromise;
    if (window.google?.maps?.marker?.AdvancedMarkerElement) {
        _mapsApiPromise = Promise.resolve(window.google.maps);
        return _mapsApiPromise;
    }
    const loadPromise = new Promise((resolve, reject) => {
        const cbName = '__mdGmapReady_' + Date.now();
        window[cbName] = () => {
            delete window[cbName];
            resolve(window.google.maps);
        };
        const script = document.createElement('script');
        script.src = [
            'https://maps.googleapis.com/maps/api/js',
            `?key=${encodeURIComponent(apiKey)}`,
            '&libraries=marker',
            `&callback=${cbName}`,
            '&loading=async',
            '&v=weekly',
        ].join('');
        script.async = true;
        script.defer = true;
        script.onerror = () => {
            _mapsApiPromise = null;
            reject(new Error('Google Maps API script failed to load'));
        };
        document.head.appendChild(script);
    });
    const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => {
            _mapsApiPromise = null;
            reject(new Error('Google Maps API load timeout'));
        }, 10000)
    );
    _mapsApiPromise = Promise.race([loadPromise, timeoutPromise]);
    return _mapsApiPromise;
}

function loadMarkerClusterer() {
    if (_markerClustererPromise) return _markerClustererPromise;
    if (window.markerClusterer?.MarkerClusterer) {
        _markerClustererPromise = Promise.resolve(window.markerClusterer);
        return _markerClustererPromise;
    }
    const loadPromise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/@googlemaps/markerclusterer/dist/index.min.js';
        script.async = true;
        script.defer = true;
        script.onload = () => resolve(window.markerClusterer || null);
        script.onerror = () => {
            _markerClustererPromise = null;
            reject(new Error('Google Maps MarkerClusterer failed to load'));
        };
        document.head.appendChild(script);
    });
    const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => {
            _markerClustererPromise = null;
            reject(new Error('Google Maps MarkerClusterer load timeout'));
        }, 8000)
    );
    _markerClustererPromise = Promise.race([loadPromise, timeoutPromise]);
    return _markerClustererPromise;
}

// ownerDoc: el document del elemento raíz del widget (puede diferir del
// document global cuando Odoo renderiza la vista previa en un iframe).
// Usar ownerDoc en lugar de `document` previene que las llamadas a
// document.head.appendChild() fallen con TypeError cuando document.head
// es null durante la transición de carga del WebsiteBuilder (onIframeLoad).
function loadStylesheet(href, ownerDoc) {
    const doc = ownerDoc || document;
    if (!doc.head) return; // document en estado transitorio — saltar
    if (doc.querySelector(`link[href="${href}"]`)) return;
    const link = doc.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    doc.head.appendChild(link);
}

function loadExternalScript(src, isReady, label, ownerDoc) {
    if (isReady()) return Promise.resolve();
    const doc = ownerDoc || document;
    if (!doc.head) return Promise.reject(new Error(`${label}: document.head not available`));
    return new Promise((resolve, reject) => {
        const script = doc.createElement('script');
        script.src = src;
        script.async = true;
        script.defer = true;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`${label} failed to load`));
        doc.head.appendChild(script);
    });
}

function loadLeafletStack(ownerDoc) {
    if (_leafletPromise) return _leafletPromise;
    const doc = ownerDoc || document;
    loadStylesheet('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', doc);
    loadStylesheet('https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css', doc);
    _leafletPromise = loadExternalScript(
        'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
        () => Boolean(window.L),
        'Leaflet',
        doc
    ).then(() => loadExternalScript(
        'https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js',
        () => Boolean(window.L?.markerClusterGroup),
        'Leaflet MarkerCluster',
        doc
    )).then(() => window.L);
    return _leafletPromise;
}

// ── DNA pin HTML element (mirrors the QWeb SVG pin structure) ─────────────────
function createDnaPinElement(active = false) {
    const wrap = document.createElement('div');
    wrap.className = 'md-gmap-pin' + (active ? ' is-active' : '');
    // viewBox covers the full pin height: dot at 0,0 + helix going to -60 + tooltip at -74
    wrap.innerHTML = `
        <svg class="md-gmap-pin-svg" viewBox="-14 -78 28 82"
             xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <circle class="pin-glow" cx="0" cy="0" r="16"/>
            <g class="helix-body">
                <path class="dna-strand strand-a"
                      d="M 0,0 C 7,-10 -7,-20 0,-30 C 7,-40 -7,-50 0,-60"/>
                <path class="dna-strand strand-b"
                      d="M 0,0 C -7,-10 7,-20 0,-30 C -7,-40 7,-50 0,-60"/>
                <line class="dna-base" x1="-6" y1="-15" x2="6" y2="-15"/>
                <line class="dna-base" x1="-6" y1="-30" x2="6" y2="-30"/>
                <line class="dna-base" x1="-6" y1="-45" x2="6" y2="-45"/>
            </g>
            <circle class="pin-dot"   cx="0" cy="0" r="5"/>
            <circle class="pin-pulse" cx="0" cy="0" r="5"/>
        </svg>`;
    return wrap;
}

function createClusterIcon(count) {
    const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="54" height="54" viewBox="0 0 54 54">
            <circle cx="27" cy="27" r="24" fill="#d3222a" fill-opacity=".22"/>
            <circle cx="27" cy="27" r="18" fill="#d3222a"/>
        </svg>`;
    return {
        url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`,
        scaledSize: new google.maps.Size(54, 54),
        labelOrigin: new google.maps.Point(27, 27),
    };
}

function normalizeBranchToken(value) {
    return (value || '')
        .toString()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/^mds\s+/, '')
        .replace(/^medicine depot\s+/, '')
        .trim();
}

// ── Map style (dark, high-contrast pins) ─────────────────────────────────────
const MD_MAP_STYLE = [
    { elementType: 'geometry', stylers: [{ color: '#071316' }] },
    { elementType: 'labels.icon', stylers: [{ visibility: 'off' }] },
    { elementType: 'labels.text.fill', stylers: [{ color: '#8fb7b0' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: '#061012' }] },
    { featureType: 'administrative', elementType: 'geometry.stroke', stylers: [{ color: '#25534e' }] },
    { featureType: 'administrative.locality', elementType: 'labels.text.fill', stylers: [{ color: '#c2dfd8' }] },
    { featureType: 'landscape.natural', elementType: 'geometry', stylers: [{ color: '#0a1b1a' }] },
    { featureType: 'poi', elementType: 'geometry', stylers: [{ color: '#102421' }] },
    { featureType: 'poi', elementType: 'labels.text.fill', stylers: [{ color: '#6d958e' }] },
    { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#183330' }] },
    { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#09201f' }] },
    { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#6ea79c' }] },
    { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#234a44' }] },
    { featureType: 'road.highway', elementType: 'geometry.stroke', stylers: [{ color: '#0f2928' }] },
    { featureType: 'transit', stylers: [{ visibility: 'off' }] },
    { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#061b1d' }] },
    { featureType: 'water', elementType: 'labels.text.fill', stylers: [{ color: '#487a76' }] },
];

// ── Main widget ───────────────────────────────────────────────────────────────
publicWidget.registry.MdBranchesGMap = publicWidget.Widget.extend({
    selector: '.md-gmap-container[data-maps-key]',
    disabledInEditableMode: true,

    start() {
        this._super(...arguments);

        const apiKey  = (this.el.dataset.mapsKey || '').trim();
        this._mapId   = this.el.dataset.mapsId   || 'DEMO_MAP_ID';
        this._root    = this.el.closest('.s_md_branches');
        this._center  = {
            lat: parseFloat(this.el.dataset.centerLat || '19.8'),
            lng: parseFloat(this.el.dataset.centerLng || '-89.4'),
        };
        this._zoom    = parseInt(this.el.dataset.zoom || '7', 10);
        this._canvas  = this.el.querySelector('.md-gmap-canvas');
        this._fallback = this.el.querySelector('.md-gmap-fallback');
        this._markers = [];
        this._markerByToken = new Map();
        this._infoWindow = null;
        this._cluster = null;
        this._leaflet = null;
        this._leafletMap = null;
        this._leafletGroup = null;
        this._leafletMarkerByToken = new Map();
        this._leafletMarkers = [];

        let branches = [];
        try { branches = JSON.parse(this.el.dataset.branches || '[]'); }
        catch { branches = []; }
        this._branches = branches
            .filter(b => b.lat && b.lng)
            .map((branch) => ({
                ...branch,
                state_key: (branch.state_key || '').toLowerCase(),
                city: branch.city || branch.name || '',
                _token_name: normalizeBranchToken(branch.name || ''),
                _token_city: normalizeBranchToken(branch.city || branch.name || ''),
            }));

        if (!this._canvas || !this._branches.length) {
            return;
        }

        if (!apiKey || apiKey === 'missing') {
            this._initLeafletMap();
            return;
        }

        loadGoogleMapsAPI(apiKey)
            .then(maps => this._initMap(maps))
            .catch((err) => {
                console.warn('[MD] Google Maps not available:', err.message);
                this._initLeafletMap();
            });
    },

    _initLeafletMap() {
        // Guard: el elemento puede haber sido desconectado del DOM por el editor
        // entre que se invocó start() y que la promesa de carga se resuelve.
        // ownerDocument.head puede ser null si estamos en el iframe transitorio
        // del WebsiteBuilder (onIframeLoad). Ambas condiciones deben ser válidas.
        if (!this.el?.isConnected) return;
        const ownerDoc = this.el.ownerDocument;
        if (!ownerDoc?.head) return;

        loadLeafletStack(ownerDoc)
            .then((L) => {
                // Re-verificar después de la carga asíncrona (el widget puede
                // haber sido destruido mientras Leaflet descargaba).
                if (!this.el?.isConnected) return;
                this._leaflet = L;
                this._fallback?.setAttribute('hidden', '');
                this._canvas.removeAttribute('hidden');

                this._leafletMap = L.map(this._canvas, {
                    center: [this._center.lat, this._center.lng],
                    zoom: this._zoom,
                    scrollWheelZoom: false,
                    zoomControl: true,
                });

                // Fondo oscuro inmediato en el contenedor (fallback AdBlocker)
                this._canvas.style.background = '#0d1b1a';

                // Activar clase de dark mode en el canvas (dispara el filtro CSS)
                this._canvas.classList.add('md-leaflet-dark');

                const tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                    maxZoom: 19,
                });

                // Suprimir iconos de imagen rota cuando AdBlockers bloquean tiles
                tileLayer.on('tileerror', (evt) => {
                    if (evt.tile) {
                        evt.tile.style.display = 'none';
                    }
                });

                tileLayer.addTo(this._leafletMap);

                this._leafletGroup = L.markerClusterGroup({
                    iconCreateFunction: (cluster) => L.divIcon({
                        html: `<span>${cluster.getChildCount()}</span>`,
                        className: 'md-map-cluster',
                        iconSize: L.point(54, 54),
                    }),
                    showCoverageOnHover: false,
                    spiderfyOnMaxZoom: true,
                });

                const bounds = [];
                this._branches.forEach((branch, idx) => {
                    const marker = L.marker([branch.lat, branch.lng], {
                        title: branch.name,
                        icon: L.divIcon({
                            html: createDnaPinElement(idx === 0).outerHTML,
                            className: 'md-leaflet-pin-shell',
                            iconSize: L.point(28, 80),
                            iconAnchor: L.point(14, 78),
                            popupAnchor: L.point(0, -74),
                        }),
                    });
                    const entry = {
                        marker,
                        branch,
                        state: branch.state_key || '',
                        tokenName: branch._token_name,
                        tokenCity: branch._token_city,
                    };
                    marker.bindPopup(this._buildInfoHTML(branch), {
                        className: 'md-leaflet-popup',
                        maxWidth: 260,
                    });
                    marker.on('click', () => this._onLeafletMarkerClick(entry));
                    this._leafletGroup.addLayer(marker);
                    this._leafletMarkers.push(entry);
                    if (entry.tokenName) this._leafletMarkerByToken.set(entry.tokenName, entry);
                    if (entry.tokenCity) this._leafletMarkerByToken.set(entry.tokenCity, entry);
                    bounds.push([branch.lat, branch.lng]);
                });

                this._leafletMap.addLayer(this._leafletGroup);
                if (bounds.length) {
                    this._leafletMap.fitBounds(bounds, { padding: [32, 32] });
                }

                this._wireLeafletCardHover();
                this._bindBridgeEvents();
                this._focusState('all');
            })
            .catch(err => console.warn('[MD] Leaflet not available:', err.message));
    },

    _initMap(maps) {
        const { Map, InfoWindow } = maps;
        const { AdvancedMarkerElement } = maps.marker;
        this._maps = maps;

        // Switch visibility: hide SVG, show canvas
        this._fallback?.setAttribute('hidden', '');
        this._canvas.removeAttribute('hidden');

        this._map = new Map(this._canvas, {
            center:             this._center,
            zoom:               this._zoom,
            mapId:              this._mapId,
            disableDefaultUI:   true,
            zoomControl:        true,
            gestureHandling:    'cooperative',
            mapTypeControl:     false,
            streetViewControl:  false,
            fullscreenControl:  false,
            styles:             MD_MAP_STYLE,
        });

        this._infoWindow = new InfoWindow({ maxWidth: 260 });

        this._branches.forEach((branch, idx) => {
            const pinEl = createDnaPinElement(idx === 0);
            const marker = new AdvancedMarkerElement({
                map:      this._map,
                position: { lat: branch.lat, lng: branch.lng },
                content:  pinEl,
                title:    branch.name,
            });
            const entry = {
                marker,
                pinEl,
                branch,
                state: branch.state_key || '',
                tokenName: branch._token_name,
                tokenCity: branch._token_city,
            };
            marker.addListener('click', () => this._onMarkerClick(entry));
            this._markers.push(entry);
            if (entry.tokenName) this._markerByToken.set(entry.tokenName, entry);
            if (entry.tokenCity) this._markerByToken.set(entry.tokenCity, entry);
        });

        // Wire up card hover → map marker pulse
        const cards = this._root?.querySelectorAll('.md-branch-card[data-branch-city]') || [];
        cards.forEach((card) => {
            const token = normalizeBranchToken(card.dataset.branchCity || card.dataset.branchName || '');
            const entry = this._markerByToken.get(token);
            card.addEventListener('mouseenter', () => {
                entry?.pinEl.classList.add('is-active');
            });
            card.addEventListener('mouseleave', () => {
                entry?.pinEl.classList.remove('is-active');
            });
        });

        this._bindBridgeEvents();
        this._focusState('all');
        this._initMarkerClusterer();
    },

    _initMarkerClusterer() {
        if (!this._map || this._markers.length < 2) return;
        loadMarkerClusterer()
            .then((clusterer) => {
                if (!clusterer?.MarkerClusterer || !this._map) return;
                this._cluster = new clusterer.MarkerClusterer({
                    map: this._map,
                    markers: this._markers.map(({ marker }) => marker),
                    renderer: {
                        render: ({ count, position }) => {
                            return new this._maps.Marker({
                                position,
                                icon: createClusterIcon(count),
                                label: {
                                    text: String(count),
                                    color: '#ffffff',
                                    fontSize: '14px',
                                    fontWeight: '900',
                                },
                                zIndex: Number(this._maps.Marker.MAX_ZINDEX) + count,
                            });
                        },
                    },
                });
            })
            .catch(err => console.warn('[MD] MarkerClusterer not available:', err.message));
    },

    _onMarkerClick(entry) {
        this._setActiveMarker(entry);

        // InfoWindow with brand HTML
        this._infoWindow.setContent(this._buildInfoHTML(entry.branch));
        this._infoWindow.open({ anchor: entry.marker, map: this._map });

        // Scroll & highlight card
        const card = document.querySelector(
            `.md-branch-card[data-branch-name="${CSS.escape(entry.branch.name)}"]`
        );
        if (card) {
            card.classList.add('is-selected');
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            setTimeout(() => card.classList.remove('is-selected'), 3000);
        }
    },

    _onLeafletMarkerClick(entry) {
        const card = document.querySelector(
            `.md-branch-card[data-branch-name="${CSS.escape(entry.branch.name)}"]`
        );
        if (card) {
            card.classList.add('is-selected');
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            setTimeout(() => card.classList.remove('is-selected'), 3000);
        }
    },

    _bindBridgeEvents() {
        if (!this._root) return;
        this._onStateChange = (ev) => {
            const visibleBranches = ev.detail?.visibleBranches || [];
            if (visibleBranches.length) {
                this._focusBranchSet(visibleBranches);
                return;
            }
            this._focusState(ev.detail?.state || 'all');
        };
        this._onCardFocus = (ev) => {
            this._focusBranch(ev.detail || {});
        };
        this._root.addEventListener('md:branches:state-change', this._onStateChange);
        this._root.addEventListener('md:branches:card-focus', this._onCardFocus);
    },

    _focusState(state) {
        if (this._leafletMap && this._leaflet) {
            const normalizedState = (state || 'all').toLowerCase();
            const subset = normalizedState === 'all'
                ? this._leafletMarkers
                : this._leafletMarkers.filter((entry) => entry.state === normalizedState);
            if (!subset.length) return;
            const bounds = this._leaflet.latLngBounds(
                subset.map(({ branch }) => [branch.lat, branch.lng])
            );
            if (subset.length === 1) {
                this._leafletMap.setView([subset[0].branch.lat, subset[0].branch.lng], 12);
            } else {
                this._leafletMap.fitBounds(bounds, { padding: [32, 32] });
            }
            return;
        }

        if (!this._map || !this._maps?.LatLngBounds) return;

        const normalizedState = (state || 'all').toLowerCase();
        const subset = normalizedState === 'all'
            ? this._markers
            : this._markers.filter((entry) => entry.state === normalizedState);

        if (!subset.length) return;

        const bounds = new this._maps.LatLngBounds();
        subset.forEach(({ branch }) => bounds.extend({ lat: branch.lat, lng: branch.lng }));

        if (subset.length === 1) {
            this._map.panTo({ lat: subset[0].branch.lat, lng: subset[0].branch.lng });
            this._map.setZoom(12);
        } else {
            this._map.fitBounds(bounds, 80);
        }
    },

    _focusBranchSet(branches) {
        const normalizedBranches = (branches || [])
            .filter((branch) => branch.lat && branch.lng);
        if (!normalizedBranches.length) return;

        if (this._leafletMap && this._leaflet) {
            if (normalizedBranches.length === 1) {
                const branch = normalizedBranches[0];
                this._leafletMap.flyTo([branch.lat, branch.lng], 13, { duration: 0.85 });
                const entry = this._leafletMarkerByToken.get(normalizeBranchToken(branch.city || branch.name || ''));
                entry?.marker?.openPopup();
                return;
            }
            const bounds = this._leaflet.latLngBounds(normalizedBranches.map((branch) => [branch.lat, branch.lng]));
            this._leafletMap.flyToBounds(bounds, { padding: [32, 32], duration: 0.85 });
            return;
        }

        if (!this._map || !this._maps?.LatLngBounds) return;
        if (normalizedBranches.length === 1) {
            const branch = normalizedBranches[0];
            this._map.panTo({ lat: branch.lat, lng: branch.lng });
            this._map.setZoom(13);
            const entry = this._markerByToken.get(normalizeBranchToken(branch.city || branch.name || ''));
            if (entry) {
                this._setActiveMarker(entry);
                this._infoWindow?.setContent(this._buildInfoHTML(entry.branch));
                this._infoWindow?.open({ anchor: entry.marker, map: this._map });
            }
            return;
        }
        const bounds = new this._maps.LatLngBounds();
        normalizedBranches.forEach((branch) => bounds.extend({ lat: branch.lat, lng: branch.lng }));
        this._map.fitBounds(bounds, 80);
    },

    _focusBranch(detail) {
        if (this._leafletMap) {
            const tokens = [
                normalizeBranchToken(detail.name || ''),
                normalizeBranchToken(detail.city || ''),
            ].filter(Boolean);
            const entry = tokens.map((token) => this._leafletMarkerByToken.get(token)).find(Boolean);
            if (!entry) return;
            this._leafletMap.flyTo([entry.branch.lat, entry.branch.lng], 13, { duration: 0.85 });
            entry.marker.openPopup();
            return;
        }

        if (!this._map) return;
        const tokens = [
            normalizeBranchToken(detail.name || ''),
            normalizeBranchToken(detail.city || ''),
        ].filter(Boolean);
        const entry = tokens.map((token) => this._markerByToken.get(token)).find(Boolean);
        if (!entry) return;

        this._setActiveMarker(entry);
        this._map.panTo({ lat: entry.branch.lat, lng: entry.branch.lng });
        this._map.setZoom(Math.max(13, this._map.getZoom() || 13));
        this._infoWindow?.setContent(this._buildInfoHTML(entry.branch));
        this._infoWindow?.open({ anchor: entry.marker, map: this._map });
    },

    _setActiveMarker(activeEntry) {
        this._markers.forEach(({ pinEl }) => pinEl.classList.remove('is-active'));
        activeEntry?.pinEl.classList.add('is-active');
    },

    _wireLeafletCardHover() {
        const cards = this._root?.querySelectorAll('.md-branch-card[data-branch-city]') || [];
        cards.forEach((card) => {
            const token = normalizeBranchToken(card.dataset.branchCity || card.dataset.branchName || '');
            const entry = this._leafletMarkerByToken.get(token);
            card.addEventListener('mouseenter', () => {
                entry?.marker.getElement()?.querySelector('.md-gmap-pin')?.classList.add('is-active');
            });
            card.addEventListener('mouseleave', () => {
                entry?.marker.getElement()?.querySelector('.md-gmap-pin')?.classList.remove('is-active');
            });
        });
    },

    _buildInfoHTML(branch) {
        const safeName    = _esc(branch.name);
        const safeAddress = _esc(branch.address);
        const safePhone   = _esc(branch.phone);
        const safePhone2  = (branch.phone || '').replace(/\s/g, '');
        const phone = branch.phone
            ? `<a href="tel:${_esc(safePhone2)}">${safePhone}</a>`
            : '';
        return `
            <div class="md-gmap-infowin">
                <strong>${safeName}</strong>
                <p>${safeAddress}</p>
                ${phone}
                <a href="${_esc(branch.maps_url)}" target="_blank" rel="noopener">
                    Cómo llegar →
                </a>
            </div>`;
    },

    destroy() {
        if (this._root && this._onStateChange) {
            this._root.removeEventListener('md:branches:state-change', this._onStateChange);
        }
        if (this._root && this._onCardFocus) {
            this._root.removeEventListener('md:branches:card-focus', this._onCardFocus);
        }
        this._markers.forEach(({ marker }) => {
            marker.map = null;
        });
        this._cluster?.clearMarkers?.();
        this._cluster = null;
        this._leafletGroup?.clearLayers?.();
        this._leafletMap?.remove?.();
        this._leaflet = null;
        this._leafletMap = null;
        this._leafletGroup = null;
        this._leafletMarkerByToken.clear();
        this._leafletMarkers = [];
        this._markers = [];
        this._markerByToken.clear();
        this._infoWindow?.close();
        this._super(...arguments);
    },
});

export default publicWidget.registry.MdBranchesGMap;
