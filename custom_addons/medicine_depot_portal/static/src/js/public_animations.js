/** @odoo-module **/
// Medicine Depot · Animation engine
// Intersection Observer scroll triggers, counter tween, skeleton loading,
// ripple effect. Respects prefers-reduced-motion in all paths.

const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const observerRegistry = new Map();
let cleanupHandlersBound = false;
let rippleDelegationBound = false;

function registerObserver(root, observer) {
    const key = root || document;
    const set = observerRegistry.get(key) || new Set();
    set.add(observer);
    observerRegistry.set(key, set);
}

function disconnectAllObservers() {
    observerRegistry.forEach((set) => {
        set.forEach((observer) => observer.disconnect());
    });
    observerRegistry.clear();
}

function bindCleanupHandlers() {
    if (cleanupHandlersBound) return;
    cleanupHandlersBound = true;
    document.addEventListener('website_destroyed', () => {
        disconnectAllObservers();
    });
    window.addEventListener('pagehide', () => {
        disconnectAllObservers();
    }, { once: true });
}

// ── Intersection Observer: scroll-trigger reveals ─────────────────────────────
function initScrollReveals(root = document) {
    const targets = root.querySelectorAll(
        '.md-reveal, .md-reveal--fade, .md-reveal--slide-left, .md-reveal--slide-right, .md-reveal--scale'
    );
    if (!targets.length) return;

    if (prefersReduced) {
        targets.forEach(el => el.classList.add('is-visible'));
        return;
    }

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach(({ target, isIntersecting }) => {
                if (isIntersecting) {
                    target.classList.add('is-visible');
                    observer.unobserve(target);
                }
            });
        },
        { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );

    registerObserver(root, observer);
    targets.forEach(el => observer.observe(el));
}

// ── Product card stagger (grid items) ─────────────────────────────────────────
function initCardStagger(root = document) {
    const grids = root.querySelectorAll('.md-product-grid');
    if (!grids.length) return;

    if (prefersReduced) {
        grids.forEach((grid) => {
            grid.classList.remove('md-product-grid--stagger');
            grid.querySelectorAll('.md-product-card').forEach((card) => card.classList.add('is-visible'));
        });
        return;
    }

    grids.forEach((grid) => {
        grid.classList.add('md-product-grid--stagger');
        grid.querySelectorAll('.md-product-card').forEach((card) => card.classList.remove('is-visible'));
    });

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach(({ target, isIntersecting }) => {
                if (!isIntersecting) return;
                const cards = target.querySelectorAll('.md-product-card');
                cards.forEach((card, i) => {
                    setTimeout(() => card.classList.add('is-visible'), i * 60);
                });
                observer.unobserve(target);
            });
        },
        { threshold: 0.08 }
    );

    registerObserver(root, observer);
    grids.forEach(grid => observer.observe(grid));
}

// ── Counter tween ─────────────────────────────────────────────────────────────
function animateCounter(el) {
    const target = parseFloat(el.dataset.target || el.textContent || '0');
    const duration = parseInt(el.dataset.duration || '2000', 10);
    const suffix = el.dataset.suffix || '';
    const decimals = el.dataset.decimals ? parseInt(el.dataset.decimals, 10) : 0;
    const start = performance.now();
    const from = parseFloat(el.dataset.from || '0');

    if (prefersReduced) {
        el.textContent = target.toFixed(decimals) + suffix;
        return;
    }

    function ease(t) {
        return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    }

    function tick(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const value = from + (target - from) * ease(progress);
        el.textContent = value.toFixed(decimals) + suffix;
        if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
}

function initCounters(root = document) {
    const counters = root.querySelectorAll('.md-counter[data-target]');
    if (!counters.length) return;

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach(({ target, isIntersecting }) => {
                if (isIntersecting) {
                    animateCounter(target);
                    observer.unobserve(target);
                }
            });
        },
        { threshold: 0.5 }
    );

    registerObserver(root, observer);
    counters.forEach(el => observer.observe(el));
}

// ── Ripple effect ─────────────────────────────────────────────────────────────
function initRipple() {
    if (rippleDelegationBound) return;
    rippleDelegationBound = true;
    document.addEventListener('click', (ev) => {
        if (prefersReduced) return;
        const clicked = ev.target instanceof Element ? ev.target : null;
        if (!clicked) return;
        const target = clicked.closest('.md-ripple, .md-btn--primary, .md-btn-primary');
        if (!target) return;

        const rect = target.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const wave = document.createElement('span');
        wave.className = 'md-ripple-wave';
        wave.style.cssText = `width:${size}px;height:${size}px;left:${ev.clientX - rect.left - size / 2}px;top:${ev.clientY - rect.top - size / 2}px;`;
        target.appendChild(wave);
        wave.addEventListener('animationend', () => wave.remove(), { once: true });
    });
}

// ── Dark mode toggle ──────────────────────────────────────────────────────────
function initDarkModeToggle() {
    const toggle = document.querySelector('[data-md-dark-toggle]');
    if (!toggle) return;

    const root = document.querySelector('.md-bento-public') || document.body;
    const stored = localStorage.getItem('md-color-scheme');
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = stored ? stored === 'dark' : systemDark;

    function apply(dark) {
        root.dataset.colorScheme = dark ? 'dark' : 'light';
        toggle.setAttribute('aria-pressed', dark ? 'true' : 'false');
        toggle.setAttribute('aria-label', dark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
        localStorage.setItem('md-color-scheme', dark ? 'dark' : 'light');
    }

    apply(isDark);
    toggle.addEventListener('click', () => {
        apply(root.dataset.colorScheme !== 'dark');
    });
}

// ── Spotlight effect ──────────────────────────────────────────────────────────
function initSpotlight(root = document) {
    const tiles = root.querySelectorAll('.md-tile, .md-spotlight');
    if (!tiles.length) return;

    if (prefersReduced) return;

    tiles.forEach((tile) => {
        tile.addEventListener('mousemove', (e) => {
            const rect = tile.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            tile.style.setProperty('--mouse-x', `${x}px`);
            tile.style.setProperty('--mouse-y', `${y}px`);
        });
    });
}

// ── Init all on DOMContentLoaded ──────────────────────────────────────────────
// Guard: document.body puede ser null si este script se evalúa dentro del
// iframe transitorio del WebsiteBuilder (onIframeLoad). En ese contexto
// no hay DOM que animar; salimos limpiamente.
document.addEventListener('DOMContentLoaded', () => {
    if (!document.body) return;
    bindCleanupHandlers();
    initScrollReveals();
    initCardStagger();
    initCounters();
    initRipple();
    initDarkModeToggle();
    initSpotlight();
});
