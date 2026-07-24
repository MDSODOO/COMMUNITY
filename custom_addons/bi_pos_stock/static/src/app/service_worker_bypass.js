/** @odoo-module */
/**
 * POS service-worker bypass.
 *
 * Some Odoo/PWA service-worker builds reject dynamic POS URLs such as
 * /pos/ui/<config>/product/<uuid> or /pos/ui/<config>/stock. When a
 * FetchEvent handler rejects instead of returning a Response, the POS boot can
 * collapse with:
 * "Failed to convert value to 'Response'".
 *
 * This module keeps POS pages network-only by removing POS-related service
 * workers and caches from the controlled page as soon as the POS assets load.
 */

const POS_UI_RE = /^\/pos\/ui(?:\/|$)/;
const POS_DYNAMIC_ROUTE_RE = /^\/pos\/ui\/[^/]+\/(?:product\/[^/]+|stock|low-stock|ecommerce-orders)\/?$/;
const RELOAD_FLAG = "bi_pos_stock_sw_bypass_reloaded";

function hasReloadedAfterBypass() {
    try {
        return !!sessionStorage.getItem(RELOAD_FLAG);
    } catch (_error) {
        return true;
    }
}

function markReloadedAfterBypass() {
    try {
        sessionStorage.setItem(RELOAD_FLAG, "1");
    } catch (_error) {
        // Keep the bypass non-blocking if storage is unavailable in PWA mode.
    }
}

function clearReloadedAfterBypass() {
    try {
        sessionStorage.removeItem(RELOAD_FLAG);
    } catch (_error) {
        // Keep the bypass non-blocking if storage is unavailable in PWA mode.
    }
}

function shouldBypassPosServiceWorker() {
    const path = window.location.pathname;
    return (
        POS_UI_RE.test(path)
        || POS_DYNAMIC_ROUTE_RE.test(path)
    );
}

async function unregisterPosServiceWorkers() {
    if (!("serviceWorker" in navigator) || !shouldBypassPosServiceWorker()) {
        return false;
    }

    try {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrations.map((registration) => registration.unregister()));
        return registrations.length > 0;
    } catch (error) {
        console.warn("[bi_pos_stock] could not unregister POS service workers:", error);
        return false;
    }
}

async function clearPosCaches() {
    if (!("caches" in window) || !shouldBypassPosServiceWorker()) {
        return;
    }

    try {
        const cacheNames = await caches.keys();
        const posCacheNames = cacheNames.filter((name) => {
            const normalized = String(name).toLowerCase();
            return (
                normalized.includes("pos")
                || normalized.includes("point_of_sale")
                || normalized.includes("product")
            );
        });
        await Promise.all(posCacheNames.map((name) => caches.delete(name)));
    } catch (error) {
        console.warn("[bi_pos_stock] could not clear POS caches:", error);
    }
}

if (shouldBypassPosServiceWorker()) {
    Promise.all([unregisterPosServiceWorkers(), clearPosCaches()]).then(([unregistered]) => {
        if (
            navigator.serviceWorker?.controller
            && unregistered
            && !hasReloadedAfterBypass()
        ) {
            markReloadedAfterBypass();
            window.location.reload();
            return;
        }
        if (!navigator.serviceWorker?.controller) {
            clearReloadedAfterBypass();
        }
    }).catch((error) => {
        console.warn("[bi_pos_stock] POS service-worker bypass failed:", error);
    });
}
