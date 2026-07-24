/** @odoo-module */

import { registry } from "@web/core/registry";

/**
 * Tour: Tienda Online — Uso del badge "A la mano"
 * URL de inicio: /shop
 * Audiencia: Clientes usando la tienda por primera vez
 * Regla de negocio: Inventario físico = "A la mano" (nunca "Disponible"/"Stock")
 */
registry.category("web_tour.tours").add("md_shop_ala_mano_tour", {
    url: "/shop",
    steps: () => [
        {
            trigger: ".oe_website_sale .o_wsale_products_grid_table, .products.row",
            content:
                "<strong>Bienvenido a nuestra Tienda.</strong><br>" +
                "Aquí puedes explorar todo nuestro catálogo de productos farmacéuticos.",
            position: "bottom",
        },
        {
            trigger: ".md-ala-mano-badge, .badge-ala-mano",
            content:
                "El indicador <strong>\"A la mano\"</strong> muestra cuántas unidades " +
                "tenemos físicamente en inventario en este momento. " +
                "Esto te ayuda a planificar tus pedidos con información real.",
            position: "bottom",
        },
        {
            trigger: ".md-qty-pill, .qty-selector-pill",
            content:
                "Usa este selector para elegir la <strong>cantidad</strong> que necesitas. " +
                "No podrás pedir más de lo que tenemos <strong>A la mano</strong>.",
            position: "top",
        },
        {
            trigger: ".o_wsale_product_btn .btn-primary, button.a-buy",
            content:
                "Haz clic en <strong>Agregar al carrito</strong> para incluir " +
                "el producto en tu orden.",
            position: "left",
        },
        {
            trigger: ".o_cart_btn, a[href='/shop/cart']",
            content:
                "Tu <strong>carrito</strong> se actualiza automáticamente. " +
                "Puedes seguir comprando o proceder al pago.",
            position: "bottom",
        },
    ],
});
