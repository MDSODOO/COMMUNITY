/** @odoo-module **/

import { Component, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

class CfdiUploadField extends Component {
    static template = "purchase_invoice_parser.CfdiUploadField";
    static props = {
        ...standardFieldProps,
        accept:        { type: String, optional: true },
        label:         { type: String, optional: true },
        icon:          { type: String, optional: true },
        filenameField: { type: String, optional: true },
    };

    setup() {
        this.state = useState({ isDragOver: false });
        this.dragCount = 0;            // counter para evitar false-leave en hijos
        this.inputRef = useRef("fileInput");
        this.notification = useService("notification");
    }

    // ── Computed ────────────────────────────────────────────────────────────
    get hasFile() {
        return !!this.props.record.data[this.props.name];
    }

    get fileName() {
        return (this.props.filenameField &&
                this.props.record.data[this.props.filenameField]) || "";
    }

    // ── Drag & Drop ─────────────────────────────────────────────────────────
    onDragEnter(ev) {
        ev.preventDefault();
        this.dragCount++;
        this.state.isDragOver = true;
    }

    onDragLeave() {
        this.dragCount = Math.max(this.dragCount - 1, 0);
        if (this.dragCount === 0) this.state.isDragOver = false;
    }

    onDragOver(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "copy";
    }

    async onDrop(ev) {
        ev.preventDefault();
        this.dragCount = 0;
        this.state.isDragOver = false;
        const file = ev.dataTransfer.files[0];
        if (file) await this._processFile(file);
    }

    // ── Click / Explorer ────────────────────────────────────────────────────
    onZoneClick() {
        if (!this.props.readonly && this.inputRef.el) {
            this.inputRef.el.click();
        }
    }

    async onFileChange(ev) {
        const file = ev.target.files[0];
        if (file) await this._processFile(file);
        ev.target.value = "";          // permite re-seleccionar el mismo archivo
    }

    async clearFile() {
        const updates = { [this.props.name]: false };
        if (this.props.filenameField) updates[this.props.filenameField] = "";
        await this.props.record.update(updates);
    }

    // ── File processing ─────────────────────────────────────────────────────
    async _processFile(file) {
        if (!this._isValidType(file)) {
            this.notification.add(
                `Tipo inválido. Se esperaba: ${this.props.accept}`,
                { type: "warning", title: "Archivo no válido / Invalid file" }
            );
            return;
        }
        const base64 = await this._toBase64(file);
        const updates = { [this.props.name]: base64 };
        if (this.props.filenameField) updates[this.props.filenameField] = file.name;
        await this.props.record.update(updates);   // dispara onchange del modelo
    }

    _isValidType(file) {
        if (!this.props.accept) return true;
        const allowed = this.props.accept.split(",").map(t => t.trim().toLowerCase());
        const ext     = "." + file.name.split(".").pop().toLowerCase();
        return allowed.some(t => t === ext || t === file.type);
    }

    _toBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload  = e => resolve(e.target.result.split(",")[1]);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }
}

export const cfdiUploadField = {
    component: CfdiUploadField,
    displayName: "CFDI Upload Zone",
    supportedTypes: ["binary"],
    extractProps: ({ attrs, options }) => ({
        accept:        options.accept || attrs.accept  || "",
        label:         options.label  || attrs.label   || "Subir archivo",
        icon:          options.icon   || "fa fa-upload",
        filenameField: attrs.filename || "",
    }),
};

registry.category("fields").add("cfdi_upload", cfdiUploadField);
