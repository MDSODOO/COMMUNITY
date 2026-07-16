/** @odoo-module **/
// Medicine Depot · Bridge visual para superficies nativas de Odoo.
// 1) Normaliza enlaces legacy del menú a rutas internas.
// 2) Añade clases por ruta para styling consistente (shop/blog/portal/contacto).
// 3) Marca activo en navbar nativo (#top) y aplica estado sticky on-scroll.

const URL_NORMALIZATION = new Map([
    ["https://medicinedepot.com.mx/medicd/", "/medicd"],
    ["https://forms.gle/FJu6zr96Eu7EyB639", "/farmacovigilancia"],
    [
        "https://docs.google.com/forms/d/e/1FAIpQLSc9-Jj-g0p66gffeZmB0HSab9_YdG01_BhYmpa3fBH9oU2NJA/viewform",
        "/farmacovigilancia",
    ],
    ["/contactanos", "/contactus"],
]);

const canonicalizeHref = (rawHref) => {
    if (!rawHref) return rawHref;
    const href = rawHref.trim();

    const direct = URL_NORMALIZATION.get(href);
    if (direct) return direct;
    if (href.startsWith("/contactanos")) return "/contactus";
    if (href.startsWith("/") || href.startsWith("#")) return href;

    try {
        const parsed = new URL(href, window.location.origin);
        const host = parsed.hostname.toLowerCase();
        const path = parsed.pathname.replace(/\/+$/, "");

        if (
            (host === "medicinedepot.com.mx" || host === "www.medicinedepot.com.mx") &&
            path.endsWith("/medicd")
        ) {
            return "/medicd";
        }
        if (host === "forms.gle" || host.includes("docs.google.com")) {
            return "/farmacovigilancia";
        }
        if (host === window.location.hostname) {
            return `${parsed.pathname}${parsed.search}${parsed.hash}`;
        }
    } catch {
        return href;
    }
    return href;
};

const routeClassForPath = (path) => {
    if (path.startsWith("/shop")) return "md-route-shop";
    if (path.startsWith("/blog")) return "md-route-blog";
    if (path.startsWith("/my")) return "md-route-portal";
    if (path.startsWith("/contact") || path.startsWith("/contacto")) return "md-route-contact";
    if (path.startsWith("/medicd")) return "md-route-medicd";
    if (path.startsWith("/afiliacion")) return "md-route-afiliacion";
    if (path.startsWith("/sucursales")) return "md-route-sucursales";
    if (path.startsWith("/farmacovigilancia")) return "md-route-pharmacovigilance";
    return "md-route-public";
};

const normalizeMenuLinks = () => {
    document.querySelectorAll('a[href]').forEach((anchor) => {
        const rawHref = anchor.getAttribute("href");
        if (!rawHref) return;
        const normalized = canonicalizeHref(rawHref);
        if (normalized && normalized !== rawHref) {
            anchor.setAttribute("href", normalized);
        }
    });
};

const setNativeNavActive = () => {
    const currentPath = window.location.pathname;
    const nav = document.querySelector("#top #top_menu, #top_menu");
    if (!nav) return;

    nav.querySelectorAll("a.nav-link").forEach((link) => {
        const href = canonicalizeHref(link.getAttribute("href") || "");
        if (!href.startsWith("/")) return;
        const linkPath = (() => {
            try {
                return new URL(href, window.location.origin).pathname;
            } catch {
                return href;
            }
        })();
        const isActive = currentPath === linkPath || (linkPath !== "/" && currentPath.startsWith(`${linkPath}/`));
        link.classList.toggle("active", isActive);
        link.setAttribute("aria-current", isActive ? "page" : "false");
    });
};

const mountNativeHeaderScrollState = () => {
    const header = document.getElementById("top");
    if (!header) return;

    let ticking = false;
    const update = () => {
        header.classList.toggle("md-native-scrolled", window.scrollY > 64);
        ticking = false;
    };
    const onScroll = () => {
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(update);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    update();
};

// Guard: document.body puede ser null si este script se evalúa dentro del
// iframe transitorio del WebsiteBuilder (onIframeLoad). Salimos limpiamente.
document.addEventListener("DOMContentLoaded", () => {
    if (!document.body) return;
    const path = window.location.pathname || "/";
    const routeClass = routeClassForPath(path);
    const body = document.body;
    const wrapwrap = document.getElementById("wrapwrap");
    const wrap = document.getElementById("wrap");

    body.classList.add("md-site-unified", routeClass);
    wrapwrap?.classList.add("md-wrapwrap-unified");
    wrap?.classList.add("md-wrap-unified");

    normalizeMenuLinks();
    setNativeNavActive();
    mountNativeHeaderScrollState();
});
