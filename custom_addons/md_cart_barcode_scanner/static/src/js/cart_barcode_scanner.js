/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

const SCAN_BTN_SELECTOR = "[data-md-scan-barcode-btn]";
const SCAN_MODAL_ID = "o_md_barcode_scan_modal";
// Evento puente entre "la camara decodifico algo" y "actualizar el carrito".
// Desacopla el origen del codigo (camara real, entrada manual, o un test
// automatizado que lo dispare directo) del resto del flujo — ver
// e2e_tests/audit_cart_scanner.spec.ts.
const SCANNED_EVENT = "md_barcode_scanned";

// NOTA IMPORTANTE: este archivo NO usa publicWidget.Widget/registry a
// proposito. Se verifico en vivo (moviles reales + inspeccion de los
// handlers jQuery delegados sobre <body>) que en /shop/cart (layout de
// checkout) Odoo nunca ejecuta el escaneo/arranque de publicWidget.registry:
// ni este widget ni otros widgets legacy del sitio (ShopCartSubmitGuard,
// MdToastPromoter, etc.) llegan a adjuntar su listener ahi, aunque el
// registro de la clase si ocurre correctamente. En vez de depender de ese
// ciclo de vida poco confiable en esta pagina especifica, se delega el click
// directo sobre document, que se activa apenas el script se evalua.
let scanner = null;
// Unico gate de re-entrada: evita procesar dos escaneos/envios manuales en
// paralelo. A proposito NO depende de si la camara logro iniciar (stub sin
// vendorizar, permiso denegado, etc.) para que la entrada manual siga
// funcionando aunque la camara este completamente fuera de servicio.
let processing = false;

function openModal() {
    if (document.getElementById(SCAN_MODAL_ID)) {
        return;
    }
    const modal = renderToElement("md_cart_barcode_scanner.ScanModal", {});
    document.body.appendChild(modal);
    modal.querySelectorAll("[data-md-scan-close]").forEach((btn) => {
        btn.addEventListener("click", closeModal);
    });
    modal.querySelectorAll("[data-md-scan-manual-toggle]").forEach((btn) => {
        btn.addEventListener("click", toggleManualEntry);
    });
    modal.querySelector("[data-md-manual-submit]").addEventListener("click", submitManualCode);
    modal.querySelector("[data-md-manual-input]").addEventListener("keydown", (ev) => {
        if (ev.key === "Enter") {
            ev.preventDefault();
            submitManualCode();
        }
    });
}

function closeModal() {
    const modal = document.getElementById(SCAN_MODAL_ID);
    stopCamera();
    processing = false;
    if (modal) {
        modal.remove();
    }
}

function toggleManualEntry() {
    const backdrop = document.querySelector(`#${SCAN_MODAL_ID} .o_md_manual_backdrop`);
    if (!backdrop) return;
    const opening = backdrop.classList.contains("d-none");
    backdrop.classList.toggle("d-none");
    if (opening) {
        document.querySelector(`#${SCAN_MODAL_ID} [data-md-manual-input]`)?.focus();
    }
}

function submitManualCode() {
    const input = document.querySelector(`#${SCAN_MODAL_ID} [data-md-manual-input]`);
    const code = (input?.value || "").trim();
    if (!code) return;
    toggleManualEntry();
    if (input) input.value = "";
    handleScannedBarcode(code);
}

function setModalStatus(text, status) {
    // status: 'pending' | 'ok' | 'error'
    const statusEl = document.querySelector(`#${SCAN_MODAL_ID} .o_md_scan_status`);
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.classList.remove("o_md_status_pending", "o_md_status_ok", "o_md_status_error");
    statusEl.classList.add(`o_md_status_${status}`);
}

async function startCamera() {
    // formatsToSupport explicito: los productos de la farmacia usan codigos
    // 1D (EAN13/UPC/Code128), no QR. Sin esto el default de la libreria
    // puede priorizar QR y perder precision en 1D.
    const formats = window.Html5QrcodeSupportedFormats;
    scanner = new window.Html5Qrcode("md_barcode_reader", {
        formatsToSupport: formats
            ? [formats.EAN_13, formats.EAN_8, formats.UPC_A, formats.UPC_E, formats.CODE_128, formats.CODE_39, formats.QR_CODE]
            : undefined,
        verbose: false,
    });
    await scanner.start(
        { facingMode: "environment" },
        // qrbox RECTANGULAR (no cuadrado): un codigo de barras 1D es ancho y
        // bajo. Un recuadro cuadrado (230x230, el que hubo aqui durante el
        // rediseno visual para calzar con las esquinas del mockup) recorta
        // mal el codigo y rompe la deteccion real en el celular — bug
        // reportado en vivo tras el pulido de diseno. 250x150 es el valor
        // original, funcional, de antes del rediseno.
        { fps: 10, qrbox: { width: 250, height: 150 } },
        (decodedText) => {
            // Camara real: reemite como el mismo evento que dispara un test
            // o la entrada manual.
            document.dispatchEvent(new CustomEvent(SCANNED_EVENT, { detail: { barcode: decodedText } }));
        },
        () => {} // ruido normal por frame sin codigo detectado: se ignora
    );
}

async function stopCamera() {
    if (scanner) {
        try {
            await scanner.stop();
            scanner.clear();
        } catch (err) {
            // camara ya liberada (p.ej. modal cerrado antes de iniciar)
        }
    }
    scanner = null;
}

async function onOpenScanner(ev) {
    ev.preventDefault();
    // El modal se abre SIEMPRE primero: es el unico canal de feedback
    // confiable en paginas publicas (el servicio "notification" del
    // backend no esta disponible en el bundle del sitio, así que un
    // toast ahi se pierde en silencio).
    openModal();
    if (!window.Html5Qrcode) {
        setModalStatus(_t("El lector de codigo de barras no esta disponible en este dispositivo todavia. Usa la entrada manual."), "error");
        return;
    }
    try {
        await startCamera();
    } catch (err) {
        setModalStatus(_t("No se pudo acceder a la camara. Usa la entrada manual o verifica los permisos del navegador."), "error");
    }
}

async function handleScannedBarcode(barcode) {
    if (!barcode || processing) {
        return; // evita doble disparo mientras se procesa el RPC anterior
    }
    processing = true;
    setModalStatus(_t("Buscando producto..."), "pending");

    let result;
    try {
        result = await rpc("/shop/cart/scan_barcode", { barcode, quantity: 1 });
    } catch (err) {
        setModalStatus(_t("Error de conexion al agregar el producto."), "error");
        processing = false;
        return;
    }

    if (!result.success) {
        setModalStatus(result.message || _t("No se pudo agregar el producto."), "error");
        processing = false; // permite reintentar sin reabrir el modal
        return;
    }

    setModalStatus(_t('Producto añadido. Cantidad "A la mano": %s', result.qty_on_hand ?? result.added_qty), "ok");
    // Pausa breve para que el mensaje de exito sea visible antes de
    // recargar (el modal se destruye junto con el resto del DOM).
    await new Promise((resolve) => setTimeout(resolve, 900));
    closeModal();
    window.location.reload(); // refresca lineas/subtotal del carrito
}

document.addEventListener("click", (ev) => {
    const btn = ev.target.closest?.(SCAN_BTN_SELECTOR);
    if (btn) {
        onOpenScanner(ev);
    }
});

document.addEventListener(SCANNED_EVENT, (ev) => handleScannedBarcode(ev.detail?.barcode));
