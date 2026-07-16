/** @odoo-module **/
// Medicine Depot · Sucursales — Fase 3
// M1:  Pin ↔ card sync (click pin → scroll+highlight card; hover card → pulse pin)
// M8:  Tabs filtro por estado
// M11: Open/closed badge basado en hora del sistema
// M13: Copy address to clipboard
// M24: IntersectionObserver entrance animations (cards fade-in staggered)
// M27: Web Share API
// M29: Keyboard navigation en pines SVG

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.MdBranchesInteractive = publicWidget.Widget.extend({
    selector: '.s_md_branches',
    disabledInEditableMode: false,

    start() {
        this._super(...arguments);
        this.el.classList.add('is-js-ready');
        this.el.dataset.stateFocus = 'all';

        this._pins  = [...this.el.querySelectorAll('.md-dna-pin[data-pin-city]')];
        this._cards = [...this.el.querySelectorAll('.md-branch-card[data-branch-city]')];
        this._tabs  = [...this.el.querySelectorAll('.md-branches-toolbar button')];
        this._grid  = this.el.querySelector('.md-branch-cards-grid');
        this._cards.forEach((card) => {
            if (!card.hasAttribute('tabindex')) {
                card.setAttribute('tabindex', '0');
            }
        });

        this._setupOpenCloseBadges();
        this._setupEntranceAnimations();
        this._setupPinCardSync();
        this._setupTabs();
        this._setupCopyButtons();
        this._setupShareButtons();
        this._setupKeyboardNavPins();
        this._setupNearestBranch();

        const initialTab = this._tabs.find(t => t.classList.contains('is-active')) || this._tabs[0];
        if (initialTab?.dataset.state) {
            this._filterByState(initialTab.dataset.state);
        }
    },

    // ── M11: Open/closed badge ─────────────────────────────────────────────────
    _setupOpenCloseBadges() {
        const now = new Date();
        const currentMins = now.getHours() * 60 + now.getMinutes();
        const dayOfWeek = now.getDay();                // 0=dom, 6=sáb
        const isSaturday = dayOfWeek === 6;
        const isSunday   = dayOfWeek === 0;

        this.el.querySelectorAll('.md-branch-status').forEach(badge => {
            let openStr, closeStr;

            if (isSaturday && badge.dataset.openSat) {
                openStr  = badge.dataset.openSat;
                closeStr = badge.dataset.closeSat || '14:00';
            } else if (isSunday && badge.dataset.openSun) {
                openStr  = badge.dataset.openSun;
                closeStr = badge.dataset.closeSun || '13:00';
            } else if (isSaturday || isSunday) {
                // Sin datos de fin de semana → cerrado
                badge.classList.add('is-closed');
                badge.textContent = 'Cerrado';
                return;
            } else {
                openStr  = badge.dataset.open  || '09:00';
                closeStr = badge.dataset.close || '19:00';
            }

            const [oh, om] = openStr.split(':').map(Number);
            const [ch, cm] = closeStr.split(':').map(Number);
            const openMins  = oh * 60 + om;
            const closeMins = ch * 60 + cm;
            const isOpen = currentMins >= openMins && currentMins < closeMins;

            badge.classList.add(isOpen ? 'is-open' : 'is-closed');
            badge.textContent = isOpen ? 'Abierto' : 'Cerrado';
        });
    },

    // ── M24: Entrance animations (IntersectionObserver) ───────────────────────
    _setupEntranceAnimations() {
        if (!window.IntersectionObserver) {
            // Fallback: show all immediately
            this._cards.forEach(c => {
                c.classList.remove('md-will-animate');
            });
            return;
        }

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                const card = entry.target;
                const idx  = this._cards.indexOf(card);
                setTimeout(() => {
                    card.classList.add('md-animate-in');
                    card.classList.remove('md-will-animate');
                }, idx * 80);
                observer.unobserve(card);
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

        this._cards.forEach(card => observer.observe(card));

        // Fallback defensivo: si por layout no intersectan, no dejar tarjetas invisibles.
        window.setTimeout(() => {
            this._cards.forEach((card) => {
                card.classList.remove('md-will-animate');
            });
        }, 1500);
    },

    // ── M1: Pin ↔ Card sync ────────────────────────────────────────────────────
    _setupPinCardSync() {
        // Pin click → scroll to card + highlight
        this._pins.forEach(pin => {
            pin.addEventListener('click', () => {
                const city = pin.dataset.pinCity;
                const card = this._findCardByCity(city);
                if (card) this._activateCard(card, pin);
            });
        });

        // Card hover → highlight pin
        this._cards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                const city = card.dataset.branchCity;
                const pin  = this._findPinByCity(city);
                pin?.classList.add('is-hovered');
            });
            card.addEventListener('mouseleave', () => {
                this._pins.forEach(p => p.classList.remove('is-hovered'));
            });
            card.addEventListener('click', (ev) => {
                if (ev.target.closest('a, button')) return;
                this._activateCard(card, this._findPinByCity(card.dataset.branchCity));
            });
            card.addEventListener('keydown', (ev) => {
                if (!['Enter', ' '].includes(ev.key)) return;
                ev.preventDefault();
                this._activateCard(card, this._findPinByCity(card.dataset.branchCity));
            });
        });
    },

    _activateCard(card, triggerPin) {
        // Deselect all
        this._cards.forEach(c => c.classList.remove('is-selected'));
        this._pins.forEach(p => p.classList.remove('is-selected'));

        card.classList.add('is-selected');
        triggerPin?.classList.add('is-selected');

        this._emit('md:branches:card-focus', {
            name: card.dataset.branchName || '',
            city: card.dataset.branchCity || '',
            state: card.dataset.branchState || '',
            lat: parseFloat(card.dataset.branchLat || '0'),
            lng: parseFloat(card.dataset.branchLng || '0'),
        });

        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        card.focus({ preventScroll: true });

        // Auto-deselect after 3s
        clearTimeout(this._selectTimeout);
        this._selectTimeout = setTimeout(() => {
            card.classList.remove('is-selected');
            triggerPin?.classList.remove('is-selected');
        }, 3000);
    },

    _findCardByCity(city) {
        const target = this._normalizeBranchToken(city);
        if (!target) return null;
        return this._cards.find((c) => {
            const cardCity = this._normalizeBranchToken(c.dataset.branchCity || '');
            const cardName = this._normalizeBranchToken(c.dataset.branchName || '');
            return cardCity === target || cardName.includes(target) || target.includes(cardCity);
        }) || null;
    },

    _findPinByCity(city) {
        const target = this._normalizeBranchToken(city);
        if (!target) return null;
        return this._pins.find((p) =>
            this._normalizeBranchToken(p.dataset.pinCity || '') === target
        ) || null;
    },

    _normalizeBranchToken(value) {
        return (value || '')
            .toString()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .replace(/^mds\s+/, '')
            .replace(/^medicine depot\s+/, '')
            .trim();
    },

    // ── M8: Tabs filtro ────────────────────────────────────────────────────────
    _setupTabs() {
        if (!this._tabs.length) return;

        this._tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const state = tab.dataset.filterType === 'city' ? 'all' : (tab.dataset.state || 'all');
                const city = tab.dataset.filterType === 'city' ? tab.dataset.city : '';
                this._filterByState(state, { city });

                this._tabs.forEach(t => {
                    t.classList.remove('is-active');
                    t.setAttribute('aria-selected', 'false');
                });
                tab.classList.add('is-active');
                tab.setAttribute('aria-selected', 'true');

                // Highlight SVG state
                this._highlightSvgState(city ? 'all' : state);
            });
        });
    },

    _filterByState(state, options = {}) {
        this.el.dataset.stateFocus = state || 'all';
        const cityFilter = this._normalizeBranchToken(options.city || '');
        let visibleCount = 0;
        const visibleBranches = [];
        this._cards.forEach(card => {
            const cardState = card.dataset.branchState || 'all';
            const cardCity = this._normalizeBranchToken(card.dataset.branchCity || card.dataset.branchName || '');
            const showByState = state === 'all' || cardState === state;
            const showByCity = !cityFilter || cardCity === cityFilter;
            const show = showByState && showByCity;
            card.hidden = !show;
            card.setAttribute('aria-hidden', show ? 'false' : 'true');
            if (show) {
                visibleCount += 1;
                visibleBranches.push({
                    name: card.dataset.branchName || '',
                    city: card.dataset.branchCity || '',
                    state: card.dataset.branchState || '',
                    lat: parseFloat(card.dataset.branchLat || '0'),
                    lng: parseFloat(card.dataset.branchLng || '0'),
                });
            }
        });

        this._pins.forEach((pin) => {
            const pinState = (pin.dataset.pinState || '').toLowerCase();
            const show = state === 'all' || pinState === state;
            pin.classList.toggle('is-filter-hidden', !show);
            pin.setAttribute('aria-hidden', show ? 'false' : 'true');
            pin.setAttribute('tabindex', show ? '0' : '-1');
        });

        const counter = this.el.querySelector('.md-branches-meta span');
        if (counter) {
            counter.textContent = `${visibleCount} sucursales`;
        }

        if (!options.silent) {
            this._emit('md:branches:state-change', {
                state: state || 'all',
                city: options.city || '',
                visibleCount,
                visibleBranches,
            });
        }
    },

    _highlightSvgState(state) {
        const svgStates = this.el.querySelectorAll('.md-state');
        svgStates.forEach(s => s.style.filter = '');
        if (state !== 'all') {
            const target = this.el.querySelector(`.md-state--${state}`);
            if (target) target.style.filter = 'brightness(1.25) saturate(1.2)';
        }
    },

    // ── M13: Copy address ──────────────────────────────────────────────────────
    _setupCopyButtons() {
        this.el.querySelectorAll('.md-branch-copy-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const address = btn.dataset.address || '';
                try {
                    await navigator.clipboard.writeText(address);
                    btn.classList.add('is-copied');
                    const orig = btn.innerHTML;
                    btn.innerHTML = `
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M20 6 9 17l-5-5"/></svg>
                        Copiado`;
                    setTimeout(() => {
                        btn.innerHTML = orig;
                        btn.classList.remove('is-copied');
                    }, 2000);
                } catch {
                    // Fallback: select the text
                    const ta = document.createElement('textarea');
                    ta.value = address;
                    ta.style.position = 'absolute';
                    ta.style.left = '-9999px';
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand('copy');
                    ta.remove();
                }
            });
        });
    },

    // ── M27: Web Share API ─────────────────────────────────────────────────────
    _setupShareButtons() {
        this.el.querySelectorAll('.md-branch-share-btn').forEach(btn => {
            // Hide if Web Share not supported
            if (!navigator.share) {
                btn.hidden = true;
                return;
            }
            btn.addEventListener('click', async () => {
                try {
                    await navigator.share({
                        title: btn.dataset.shareTitle || 'MedicineDepot Sucursal',
                        text:  btn.dataset.shareText  || '',
                        url:   btn.dataset.shareUrl   || window.location.href,
                    });
                } catch (e) {
                    if (e.name !== 'AbortError') {
                        console.warn('[MD] Share failed:', e.message);
                    }
                }
            });
        });
    },

    // ── Sucursal más cercana (geolocalización del usuario) ─────────────────────
    _setupNearestBranch() {
        this._onUserLocation = (ev) => {
            const { lat, lng } = ev.detail || {};
            if (typeof lat !== 'number' || typeof lng !== 'number') return;
            this._highlightNearestBranch(lat, lng);
        };
        this.el.addEventListener('md:branches:user-location', this._onUserLocation);
    },

    _haversineKm(lat1, lng1, lat2, lng2) {
        const toRad = (d) => (d * Math.PI) / 180;
        const R = 6371; // radio terrestre en km
        const dLat = toRad(lat2 - lat1);
        const dLng = toRad(lng2 - lng1);
        const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    },

    _highlightNearestBranch(userLat, userLng) {
        let nearest = null;
        let minDist = Infinity;
        this._cards.forEach((card) => {
            const lat = parseFloat(card.dataset.branchLat || '');
            const lng = parseFloat(card.dataset.branchLng || '');
            if (Number.isNaN(lat) || Number.isNaN(lng)) return;
            const dist = this._haversineKm(userLat, userLng, lat, lng);
            card.classList.remove('is-nearest');
            if (dist < minDist) {
                minDist = dist;
                nearest = card;
            }
        });
        if (!nearest) return;
        nearest.classList.add('is-nearest');
        const pin = this._findPinByCity(nearest.dataset.branchCity);
        this._activateCard(nearest, pin);
    },

    // ── M29: Keyboard navigation en pines SVG ─────────────────────────────────
    _setupKeyboardNavPins() {
        this._pins.forEach(pin => {
            pin.addEventListener('keydown', (ev) => {
                if (ev.key === 'Enter' || ev.key === ' ') {
                    ev.preventDefault();
                    pin.click();
                }
            });
        });
    },

    _emit(name, detail) {
        this.el.dispatchEvent(new CustomEvent(name, {
            detail,
            bubbles: true,
        }));
    },

    destroy() {
        clearTimeout(this._selectTimeout);
        if (this._onUserLocation) {
            this.el.removeEventListener('md:branches:user-location', this._onUserLocation);
        }
        this._super(...arguments);
    },
});

export default publicWidget.registry.MdBranchesInteractive;
