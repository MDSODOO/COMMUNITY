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
 *
 * Regla de negocio: no se vende a clientes no registrados -- siempre deben
 * haberse registrado antes via el portal de /afiliacion (medicine_depot_portal).
 * Por eso el selector de cliente exige elegir un res.partner que YA exista
 * (Many2XAutocomplete de solo busqueda, sin create/createEdit) -- no hay
 * captura manual de nombre/telefono/correo ni forma de crear un contacto
 * nuevo desde este dialogo.
 */

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

const MAX_IMAGES = 5;
const MAX_FILE_SIZE = 8 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

export class ImageQuoteDropDialog extends Component {
    static template = "local_ai_connector.ImageQuoteDropDialog";
    static components = { Dialog, Many2XAutocomplete };
    static props = { close: Function };

    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.fileInputRef = useRef("fileInput");
        this.state = useState({
            files: [], // { file, previewUrl }
            partnerId: null,
            partnerDisplayName: "",
            partnerPhone: "",
            partnerEmail: "",
            dragActive: false,
            loading: false,
            result: null, // { success, message, reference }
        });

        this.onPaste = this.onPaste.bind(this);
        onMounted(() => window.addEventListener("paste", this.onPaste));
        onWillUnmount(() => window.removeEventListener("paste", this.onPaste));
    }

    onPaste(ev) {
        const items = ev.clipboardData?.items;
        if (!items) return;
        const imageFiles = [];
        for (const item of items) {
            if (item.type.startsWith("image/")) {
                const file = item.getAsFile();
                if (file) imageFiles.push(file);
            }
        }
        if (imageFiles.length) {
            ev.preventDefault();
            this.addFiles(imageFiles);
        }
    }

    // Props fijas del selector de cliente (Many2XAutocomplete standalone
    // sobre res.partner -- mismo componente que usa el widget many2one
    // nativo, pero instanciado sin un Record/vista detras, siguiendo el
    // patron de im_livechat/expertise_tags_autocomplete.js). Antes este
    // "selector" era solo un <input> de texto sin ninguna relacion con
    // res.partner -- ver auditoria.
    //
    // activeActions sin create/createEdit a proposito: regla de negocio,
    // no se vende a clientes no registrados -- el cliente SIEMPRE tiene que
    // haberse registrado antes via el portal de /afiliacion (mismo criterio
    // que ese flujo). Este dialogo no debe poder crear un contacto nuevo al
    // vuelo, solo buscar y seleccionar uno que ya exista.
    get partnerAutocompleteProps() {
        return {
            resModel: "res.partner",
            fieldString: "Cliente",
            placeholder: "🔍 Buscar por nombre, teléfono o folio de cliente registrado...",
            activeActions: { create: false, createEdit: false, write: false },
            isToMany: false,
            getDomain: () => [],
            value: this.state.partnerDisplayName,
            update: this.onPartnerUpdate.bind(this),
        };
    }

    clearPartner() {
        this.state.partnerId = null;
        this.state.partnerDisplayName = "";
        this.state.partnerPhone = "";
        this.state.partnerEmail = "";
    }

    async onPartnerUpdate(records) {
        if (!records || !records.length) {
            this.state.partnerId = null;
            this.state.partnerDisplayName = "";
            this.state.partnerPhone = "";
            this.state.partnerEmail = "";
            return;
        }
        const [partner] = records;
        this.state.partnerId = partner.id;
        this.state.partnerDisplayName = partner.display_name || "";
        // El resultado del autocomplete solo trae id/display_name -- se
        // completa telefono/correo con una lectura aparte, solo para
        // mostrarle al empleado que si es el contacto correcto antes de
        // enviar (de solo lectura, ver template).
        const [full] = await this.orm.read("res.partner", [partner.id], ["phone", "email"]);
        this.state.partnerPhone = full?.phone || "";
        this.state.partnerEmail = full?.email || "";
    }

    get canSubmit() {
        return !this.state.loading && this.state.files.length > 0 && !!this.state.partnerId;
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

    removeAllFiles() {
        for (const entry of this.state.files) {
            URL.revokeObjectURL(entry.previewUrl);
        }
        this.state.files = [];
    }

    addFiles(fileList) {
        this._addFiles(fileList);
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
            formData.append("partner_id", String(this.state.partnerId));
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
