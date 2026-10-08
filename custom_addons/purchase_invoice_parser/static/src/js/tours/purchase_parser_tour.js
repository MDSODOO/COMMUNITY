/** @odoo-module */
/**
 * Tour de Capacitación: Importar XML de Proveedor (purchase_invoice_parser)
 *
 * Audiencia: Administradores de inventario y compradores nuevos.
 * Inicio:    /odoo/purchase (Lista de Órdenes de Compra)
 * Activar:   Menú Ayuda → Tours (modo debug) o vía tour_service.startTour().
 *
 * Regla de negocio crítica: inventario físico = "A la mano". NUNCA "Disponible",
 * "Stock" ni "Existencias" en textos del tour.
 */
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("purchase_parser_tour", {
    url: "/odoo/purchase",
    steps: () => [
        // ── Paso 1: Centro de notificaciones de precio ─────────────────────────
        {
            trigger: ".pip_price_notification .o_nav_entry",
            content:
                "<strong>Centro de Actualizaciones de Precio</strong><br>" +
                "Este ícono te avisa cuando detectamos un cambio en el precio de un proveedor " +
                "al importar una factura XML. El número en rojo indica cuántas actualizaciones " +
                "están pendientes de revisar o aplicar.",
            position: "bottom",
        },
        // ── Paso 2: Botón Importar XML — auto-abre el wizard ──────────────────
        {
            trigger: ".pip_import_xml_btn",
            content:
                "<strong>Importar XML de Proveedor</strong><br>" +
                "Haz clic aquí para abrir el wizard de importación de facturas CFDI 4.0. " +
                "Soporta <b>BRUDIFARMA</b> (lotes en el XML) y <b>QUIFAMESA</b> (lotes en el PDF). " +
                "El sistema detecta el proveedor automáticamente desde el nombre del archivo.",
            position: "bottom",
            run: "click",
        },
        // ── Paso 3: Modo de importación ────────────────────────────────────────
        {
            trigger: ".o_dialog [name='upload_mode']",
            content:
                "<strong>Modo de Importación</strong><br>" +
                "Elige <em>Archivos individuales</em> para importar 1 XML (y su PDF opcional), " +
                "o <em>ZIP del proveedor</em> para procesar varios CFDI de un paquete ZIP completo.",
            position: "right",
        },
        // ── Paso 4: Campo XML ──────────────────────────────────────────────────
        {
            trigger: ".o_dialog [name='xml_file']",
            content:
                "<strong>Archivo CFDI (.xml)</strong><br>" +
                "Sube aquí el XML del proveedor:<br>" +
                "• <b>BRUDIFARMA</b>: el archivo comienza con <code>2000_</code><br>" +
                "• <b>QUIFAMESA</b>: el archivo comienza con <code>QFM</code><br>" +
                "El proveedor se detecta automáticamente del nombre del archivo.",
            position: "right",
        },
        // ── Paso 5: Selección de proveedor ────────────────────────────────────
        {
            trigger: ".o_dialog [name='partner_id']",
            content:
                "<strong>Proveedor</strong><br>" +
                "Normalmente se detecta automáticamente desde el RFC del CFDI. " +
                "Si el proveedor no aparece, selecciónalo manualmente aquí. " +
                "El proveedor correcto determina qué parser de lotes se usa.",
            position: "right",
        },
        // ── Paso 6: Botón Importar ────────────────────────────────────────────
        {
            trigger: ".o_dialog button[name='action_parse_xml']",
            content:
                "<strong>Paso 1 — Importar</strong><br>" +
                "Una vez cargado el XML (y el PDF si es QUIFAMESA), haz clic en " +
                "<strong>Importar</strong>. El sistema:<br>" +
                "• Extrae todos los conceptos del CFDI<br>" +
                "• Asigna lotes y caducidades automáticamente<br>" +
                "• Detecta cambios de precio vs. tus registros actuales<br>" +
                "• Identifica el producto Odoo para cada concepto",
            position: "top",
        },
        // ── Paso 7: Resumen de lo que pasa en la revisión ────────────────────
        {
            trigger: ".o_dialog .o_form_view",
            content:
                "<strong>Paso 2 — Revisar y Confirmar</strong><br>" +
                "Después de importar, aparecerá la tabla de conceptos del CFDI:<br>" +
                "• Líneas en <span style='color:#dc3545'>rojo</span>: asigna el producto manualmente (clic en la columna Producto)<br>" +
                "• Resumen de lotes: muestra cuántos están <b>a la mano</b> y cuáles son nuevos<br>" +
                "• Cuando todo esté revisado, crea la Orden de Compra con el botón verde<br>" +
                "• Si hay cambios de precio, el ícono <i class='fa fa-line-chart'></i> se activará<br><br>" +
                "<em>¡Listo! Ya conoces el flujo completo de importación de XML.</em>",
            position: "top",
        },
    ],
});
