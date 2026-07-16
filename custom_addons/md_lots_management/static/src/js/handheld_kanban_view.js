/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { onMounted, onPatched, onWillUnmount } from "@odoo/owl";

// Lectores tipo Zebra DataWedge en modo "Keystroke Output" no siempre envían
// un Enter/terminador como keydown real: muchas veces insertan el texto
// completo de una sola vez vía el InputConnection del campo editable con
// foco (equivalente a "pegar"), sin disparar keydown por caracter y a veces
// sin ningún Enter. Por eso escuchamos TRES señales en paralelo:
//   1) keydown Enter en el input (lectores que sí mandan terminador)
//   2) evento "input" con auto-envío tras una pausa corta (lectores que solo
//      insertan texto, sin terminador)
//   3) keydown a nivel documento como respaldo (por si el foco se pierde)
// El input debe permanecer REAL y enfocado — sin foco en un campo editable,
// DataWedge no tiene dónde inyectar el escaneo.
//
// El teclado táctil: inputmode="none"/virtualkeyboardpolicy son solo señales
// que el navegador puede ignorar. Si el teclado sigue apareciendo pese a
// esto, ya no es algo resoluble desde el código web — es el IME/teclado de
// fábrica del equipo ignorando la señal; la solución real es configurar
// Android (o DataWedge) para usar un IME "mudo"/sin UI como predeterminado.
const SCAN_QUIET_MS = 400;

class HandheldKanbanController extends KanbanController {
    setup() {
        super.setup();
        this._mdScanInput = null;
        this._mdRefocusTimer = null;
        this._mdAutoSubmitTimer = null;
        this._mdOnDocKeydown = this._mdOnDocKeydown.bind(this);

        onMounted(() => {
            this._mdSetupScanInput();
            document.addEventListener("keydown", this._mdOnDocKeydown, true);
        });
        // Si Odoo remonta el buscador (ej. al aplicar el filtro por defecto
        // "A la mano" tras la carga inicial), el nodo se reemplaza.
        onPatched(() => this._mdSetupScanInput());
        onWillUnmount(() => {
            clearTimeout(this._mdRefocusTimer);
            clearTimeout(this._mdAutoSubmitTimer);
            document.removeEventListener("keydown", this._mdOnDocKeydown, true);
            document.removeEventListener("visibilitychange", this._mdRefocus);
            document.querySelector(".o_md_barcode_scan_banner")?.remove();
        });

        this._mdRefocus = () => {
            if (document.visibilityState === "visible") {
                this._mdFocusScanInput();
            }
        };
        document.addEventListener("visibilitychange", this._mdRefocus);
    }

    _mdSetupScanInput() {
        const searchViewContainer = document.querySelector(".o_cp_searchview");
        if (!searchViewContainer || searchViewContainer.dataset.mdBarcodeReady) {
            return;
        }
        searchViewContainer.dataset.mdBarcodeReady = "1";
        // setProperty(..., "important") es necesario: .o_cp_searchview trae la
        // clase Bootstrap "d-flex" (display:flex !important), que le gana a un
        // style.display normal.
        searchViewContainer.style.setProperty("display", "none", "important");

        const banner = document.createElement("div");
        banner.className = "o_md_barcode_scan_banner d-flex align-items-center gap-2 px-3 rounded-2 flex-grow-1";
        banner.style.cssText = "background: #1f2937;";
        banner.innerHTML = '<i class="fa fa-barcode fa-lg text-white"></i>';

        const input = document.createElement("input");
        input.type = "text";
        input.className = "o_md_barcode_scan_input flex-grow-1 border-0 bg-transparent text-white fw-bold";
        input.placeholder = "Escanea el código de barras…";
        input.autocomplete = "off";
        input.setAttribute("inputmode", "none");
        input.setAttribute("virtualkeyboardpolicy", "manual");
        input.style.cssText = "outline: none; box-shadow: none;";

        input.addEventListener("keydown", (ev) => {
            if (ev.key === "Enter") {
                ev.preventDefault();
                clearTimeout(this._mdAutoSubmitTimer);
                this._mdSubmitBarcode(input.value);
            }
        });
        // Respaldo: si el lector no manda Enter, se envía solo tras una
        // pausa breve sin más cambios (el escaneo llega casi instantáneo).
        input.addEventListener("input", () => {
            clearTimeout(this._mdAutoSubmitTimer);
            this._mdAutoSubmitTimer = setTimeout(() => {
                this._mdSubmitBarcode(input.value);
            }, SCAN_QUIET_MS);
        });
        input.addEventListener("blur", () => this._mdFocusScanInput());

        banner.appendChild(input);

        searchViewContainer.parentElement?.insertBefore(banner, searchViewContainer);
        this._mdScanInput = input;
        this._mdFocusScanInput();
    }

    // Respaldo adicional: si por algún motivo el foco no está en nuestro
    // input pero llegan pulsaciones reales de teclado (keydown), se procesan
    // igual en vez de perderse.
    _mdOnDocKeydown(ev) {
        if (document.activeElement === this._mdScanInput) {
            return; // ya lo maneja el listener del input
        }
        const active = document.activeElement;
        const isOtherEditable =
            active &&
            active !== document.body &&
            active !== this._mdScanInput &&
            (active.tagName === "INPUT" || active.tagName === "TEXTAREA" || active.isContentEditable);
        if (isOtherEditable) {
            return;
        }
        if (ev.key === "Enter") {
            if (this._mdDocBuffer) {
                ev.preventDefault();
                this._mdSubmitBarcode(this._mdDocBuffer);
                this._mdDocBuffer = "";
            }
            return;
        }
        if (ev.key && ev.key.length === 1) {
            this._mdDocBuffer = (this._mdDocBuffer || "") + ev.key;
            clearTimeout(this._mdDocBufferTimer);
            this._mdDocBufferTimer = setTimeout(() => {
                this._mdDocBuffer = "";
            }, SCAN_QUIET_MS);
        }
    }

    _mdFocusScanInput() {
        clearTimeout(this._mdRefocusTimer);
        this._mdRefocusTimer = setTimeout(() => this._mdScanInput?.focus(), 150);
    }

    _mdSubmitBarcode(rawValue) {
        const code = (rawValue || "").trim();
        if (this._mdScanInput) {
            this._mdScanInput.value = "";
        }
        if (!code) {
            this._mdFocusScanInput();
            return;
        }
        const searchInput = document.querySelector(".o_searchview_input");
        if (searchInput) {
            searchInput.value = code;
            searchInput.dispatchEvent(new Event("input", { bubbles: true }));
            setTimeout(() => {
                searchInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
                this._mdFocusScanInput();
            }, 50);
        } else {
            this._mdFocusScanInput();
        }
    }
}

export const handheldKanbanView = {
    ...kanbanView,
    Controller: HandheldKanbanController,
};

registry.category("views").add("md_handheld_kanban", handheldKanbanView);
