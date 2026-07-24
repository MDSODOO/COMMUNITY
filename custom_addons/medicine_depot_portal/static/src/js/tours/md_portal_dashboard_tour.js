/** @odoo-module */

import { registry } from "@web/core/registry";

/**
 * Tour: Dashboard del Portal del Cliente
 * URL de inicio: /my
 * Audiencia: Clientes ya registrados — primer acceso
 * Regla de negocio: Inventario físico = "A la mano"
 */
registry.category("web_tour.tours").add("md_portal_dashboard_tour", {
    url: "/my",
    steps: () => [
        {
            trigger: ".md-bento-dashboard",
            content:
                "<strong>Este es tu Portal de Cliente.</strong><br>" +
                "Desde aquí puedes consultar tus pedidos, facturas y entregas " +
                "en cualquier momento.",
            position: "bottom",
        },
        {
            trigger: ".md-bento-card-orders, a[href*='/my/orders']",
            content:
                "En <strong>Mis Pedidos</strong> puedes ver el historial completo " +
                "de tus órdenes de compra y su estado actual.",
            position: "right",
        },
        {
            trigger: ".md-bento-card-invoices, a[href*='/my/invoices']",
            content:
                "En <strong>Mis Facturas</strong> puedes descargar en PDF " +
                "todas las facturas CFDI 4.0 de tus compras.",
            position: "right",
        },
        {
            trigger: ".md-bento-card-pickings, a[href*='/my/pickings']",
            content:
                "En <strong>Mis Entregas</strong> puedes ver el estatus de " +
                "cada envío: preparación, tránsito y entrega confirmada.",
            position: "right",
        },
        {
            trigger: "a[href='/shop'], .md-nav-shop",
            content:
                "Visita la <strong>Tienda</strong> para explorar nuestro catálogo. " +
                "Verás la cantidad <strong>A la mano</strong> de cada producto " +
                "para que puedas planificar tus compras.",
            position: "bottom",
        },
    ],
});
