/** @odoo-module **/
// Medicine Depot · Scroll detection para el navbar glassmorphism.
// Añade/quita .is-scrolled en .md-bento-topbar según el scroll vertical.
// El CSS en public_bento_phase1.scss activa backdrop-filter al detectar la clase.

document.addEventListener('DOMContentLoaded', () => {
    if (!document.body) return; // iframe transitorio del WebsiteBuilder
    const topbar = document.querySelector('.md-bento-topbar');
    if (!topbar) return;

    const toggler = topbar.querySelector('.md-bento-toggler');
    const navLinks = topbar.querySelector('#md-bento-nav-links');
    let ticking = false;
    const threshold = 80;
    const update = () => {
        topbar.classList.toggle('is-scrolled', window.scrollY > threshold);
        ticking = false;
    };
    const requestUpdate = () => {
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(update);
    };

    const setExpanded = (expanded) => {
        if (!toggler) return;
        toggler.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        toggler.setAttribute('aria-label', expanded ? 'Cerrar navegación' : 'Abrir navegación');
    };

    const closeMobileNav = () => {
        if (!navLinks?.classList.contains('show')) return;
        const collapse = window.bootstrap?.Collapse?.getOrCreateInstance(navLinks, { toggle: false });
        if (collapse) {
            collapse.hide();
        } else {
            navLinks.classList.remove('show');
            setExpanded(false);
        }
    };

    navLinks?.addEventListener('shown.bs.collapse', () => setExpanded(true));
    navLinks?.addEventListener('hidden.bs.collapse', () => setExpanded(false));
    navLinks?.querySelectorAll('a[href]').forEach((link) => {
        link.addEventListener('click', closeMobileNav);
    });
    document.addEventListener('keydown', (ev) => {
        if (ev.key === 'Escape') closeMobileNav();
    });

    window.addEventListener('scroll', requestUpdate, { passive: true });
    update();
});
