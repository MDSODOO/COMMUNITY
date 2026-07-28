/** @odoo-module **/
/**
 * Dialogo para que un empleado cree una solicitud de cotizacion por imagen
 * SIN pasar por el formulario publico -- pensado para el caso real (ver
 * docs/AI_MODEL_ODOO_CONFIG.md §9.3): el cliente manda la foto por
 * WhatsApp (cuenta normal, sin API oficial) a un empleado, que tiene la
 * app de WhatsApp Desktop abierta y arrastra la foto directo aqui.
 *
 * Arrastrar-y-soltar entre una app de escritorio nativa y el navegador es
 * un drag-and-drop de archivos estandar de HTML5 (dataTransfer.files) --
 * no depende de que WhatsApp tenga ninguna integracion, solo de que su
 * ventana permita arrastrar un adjunto hacia afuera (comportamiento nativo
 * de las apps de escritorio de WhatsApp en Mac/Windows).
 *
 * Envia a /ai/quote_from_image/staff (auth='user') -- mismo pipeline de
 * cola/cron/revision que la via publica, ver
 * models/image_quote_request.py.
 */

import { Component, useState, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

const MAX_IMAGES = 5;
const MAX_FILE_SIZE = 8 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png"]);

export class ImageQuoteDropDialog extends Component {
    static template = "local_ai_connector.ImageQuoteDropDialog";
    static components = { Dialog };
    static props = { close: Function };

    setup() {
        this.notification = useService("notification");
        this.fileInputRef = useRef("fileInput");
        this.state = useState({
            files: [], // { file, previewUrl }
            customerName: "",
            customerPhone: "",
            customerEmail: "",
            dragActive: false,
            loading: false,
            result: null, // { success, message, reference }
        });
    }

    get canSubmit() {
        return (
            !this.state.loading &&
            this.state.files.length > 0 &&
            this.state.customerName.trim() &&
            (this.state.customerPhone.trim() || this.state.customerEmail.trim())
        );
    }

    openFilePicker() {
        this.fileInputRef.el?.click();
    }

    onFileInputChange(ev) {
        this._addFiles(ev.target.files);
        ev.target.value = ""; // permite volver a soltar el mismo archivo despues
    }

    onDragOver(ev) {
        this.state.dragActive = true;
    }

    onDragLeave(ev) {
        this.state.dragActive = false;
    }

    onDrop(ev) {
        this.state.dragActive = false;
        this._addFiles(ev.dataTransfer.files);
    }

    _addFiles(fileList) {
        const incoming = Array.from(fileList || []);
        for (const file of incoming) {
            if (this.state.files.length >= MAX_IMAGES) {
                this.notification.add(`Máximo ${MAX_IMAGES} fotos por solicitud.`, { type: "warning" });
                break;
            }
            if (!ALLOWED_TYPES.has(file.type)) {
                this.notification.add(`"${file.name}" no es JPEG/PNG, se omitió.`, { type: "warning" });
                continue;
            }
            if (file.size > MAX_FILE_SIZE) {
                this.notification.add(`"${file.name}" pesa más de 8 MB, se omitió.`, { type: "warning" });
                continue;
            }
            this.state.files.push({ file, previewUrl: URL.createObjectURL(file) });
        }
    }

    removeFile(index) {
        const [removed] = this.state.files.splice(index, 1);
        if (removed) {
            URL.revokeObjectURL(removed.previewUrl);
        }
    }

    async submit() {
        if (!this.canSubmit) {
            return;
        }
        this.state.loading = true;
        this.state.result = null;
        try {
            const formData = new FormData();
            formData.append("csrf_token", odoo.csrf_token);
            formData.append("customer_name", this.state.customerName.trim());
            formData.append("customer_phone", this.state.customerPhone.trim());
            formData.append("customer_email", this.state.customerEmail.trim());
            for (const { file } of this.state.files) {
                formData.append("images", file);
            }

            const response = await fetch("/ai/quote_from_image/staff", {
                method: "POST",
                body: formData,
            });
            const body = await response.json();
            this.state.result = body;
            if (body.success) {
                for (const { previewUrl } of this.state.files) {
                    URL.revokeObjectURL(previewUrl);
                }
                this.state.files = [];
            }
        } catch (err) {
            this.state.result = {
                success: false,
                message: "No se pudo enviar la solicitud. Intenta de nuevo.",
            };
        } finally {
            this.state.loading = false;
        }
    }
}
