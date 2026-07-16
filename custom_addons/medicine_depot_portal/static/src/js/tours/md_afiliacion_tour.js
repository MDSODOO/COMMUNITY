/** @odoo-module */

import { registry } from "@web/core/registry";

/**
 * Tour: Flujo de Afiliación Medicine Depot
 * URL de inicio: /afiliacion
 * Audiencia: Nuevos clientes — primera visita
 * Regla de negocio: Inventario físico = "A la mano" (aplicar en todos los textos)
 */
registry.category("web_tour.tours").add("md_afiliacion_tour", {
    url: "/afiliacion",
    steps: () => [
        {
            trigger: ".md-afiliacion-hero",
            content:
                "<strong>¡Bienvenido a Medicine Depot!</strong><br>" +
                "Desde aquí puedes solicitar tu afiliación como cliente. " +
                "El proceso toma menos de 2 minutos.",
            position: "bottom",
        },
        {
            trigger: "input[name='partner_name']",
            content:
                "Ingresa el <strong>nombre de tu farmacia o empresa</strong> " +
                "tal como aparece en tu RFC.",
            position: "right",
            run: "click",
        },
        {
            trigger: "input[name='email']",
            content:
                "Tu <strong>correo electrónico</strong> es donde recibirás " +
                "la confirmación de tu afiliación y tus credenciales de acceso.",
            position: "right",
        },
        {
            trigger: "input[name='phone']",
            content:
                "Número de <strong>teléfono de contacto</strong>. " +
                "Nuestro equipo comercial te contactará en menos de 24 horas.",
            position: "right",
        },
        {
            trigger: "select[name='state_id']",
            content:
                "Selecciona el <strong>estado</strong> donde se ubica tu farmacia. " +
                "Esto nos ayuda a asignarte el ejecutivo de cuenta de tu región.",
            position: "right",
        },
        {
            trigger: "button.btn-md-afiliar, button[type='submit']",
            content:
                "Cuando hayas completado el formulario, haz clic en " +
                "<strong>Enviar Solicitud</strong>. " +
                "Te confirmaremos por correo en menos de 24 horas hábiles.",
            position: "top",
        },
    ],
});
