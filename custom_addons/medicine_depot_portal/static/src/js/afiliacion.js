/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import MdWizardBase from "./md_wizard_base";

publicWidget.registry.MedicineDepotAfiliacionForm = MdWizardBase.extend({
    selector: "#afiliacion_form",

    // ── Configuración específica ───────────────────────────────────────────────
    _stepAttr:         "[data-aff-step]",
    _stepTriggerAttr:  "[data-aff-step-jump]",
    _stepJumpDataKey:  "affStepJump",
    _submitBtnSel:     "#submit_btn",
    _successScreenSel: "#success_screen",
    _errorBoxSel:      "#afiliacion_error_box",

    events: {
        "click [data-aff-next]":      "_onNext",
        "click [data-aff-back]":      "_onBack",
        "click [data-aff-step-jump]": "_onJump",
        "change .md_aff_file_input":  "_onFileChange",
        "click [data-aff-profile]":   "_onProfileSelect",
        "change [name='privacy']":    "_onPrivacyChange",
        "input .md_affiliacion_section--general .form-control": "_onGeneralInput",
        "submit":                     "_onSubmit",
    },

    // ── Ciclo de vida ──────────────────────────────────────────────────────────
    start() {
        const res = this._super(...arguments);
        this.checklistEl = this.el.querySelector("[data-aff-checklist]");
        this.progressPctEl = this.el.querySelector("[data-wizard-progress-pct]");
        this.profileInput = this.el.querySelector("#perfil_profesional");
        this._refreshAffiliacion();
        return res;
    },

    // ── File upload feedback ───────────────────────────────────────────────────
    _setFileStatus(input) {
        const status = input.parentElement.querySelector(".md_affiliacion_file_status");
        if (!status) return;
        if (input.files && input.files.length > 0) {
            status.textContent = `Archivo seleccionado: ${input.files[0].name}`;
            status.classList.add("is-selected");
        }
    },

    _onFileChange(ev) {
        this._setFileStatus(ev.currentTarget);
        this._refreshAffiliacion();
    },

    // ── Perfil profesional (segment) ───────────────────────────────────────────
    _onProfileSelect(ev) {
        const btn = ev.currentTarget;
        this.el.querySelectorAll("[data-aff-profile]").forEach((b) => b.classList.remove("is-on"));
        btn.classList.add("is-on");
        if (this.profileInput) this.profileInput.value = btn.dataset.affProfile || "";
    },

    _onPrivacyChange() {
        this._refreshAffiliacion();
    },

    _onGeneralInput() {
        this._refreshAffiliacion();
    },

    // ── Refresco de checklist + progreso (doc-aware) ───────────────────────────
    _countFilled(selector) {
        const inputs = Array.from(this.el.querySelectorAll(selector));
        const filled = inputs.filter((i) => i.files && i.files.length > 0).length;
        return { filled, total: inputs.length };
    },

    _refreshAffiliacion() {
        const activeIndex = this._getActiveStepIndex();
        const cofepris = this._countFilled(".md_affiliacion_section--cofepris .md_aff_file_input");
        const legal = this._countFilled(".md_affiliacion_section--docs .md_aff_file_input");
        const generalFilled = Array.from(
            this.el.querySelectorAll(".md_affiliacion_section--general .form-control")
        ).some((c) => (c.value || "").trim());
        const privacy = !!this.el.querySelector("[name='privacy']:checked");

        // Checklist
        if (this.checklistEl) {
            const items = [
                { label: "Datos generales", done: activeIndex > 0 || generalFilled },
                { label: `Permisos COFEPRIS (${cofepris.filled}/${cofepris.total})`, done: cofepris.total > 0 && cofepris.filled === cofepris.total },
                { label: `Documentación legal (${legal.filled}/${legal.total})`, done: legal.total > 0 && legal.filled === legal.total },
                { label: "Aviso de privacidad", done: privacy },
            ];
            this.checklistEl.innerHTML = items
                .map(
                    (it) => `
                    <div class="md_affiliacion_check_item${it.done ? " is-done" : ""}">
                        <span class="md_affiliacion_check_box">${it.done ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 7"/></svg>' : ""}</span>
                        <span>${it.label}</span>
                    </div>`
                )
                .join("");
        }

        // Progreso doc-aware
        const totalDocs = cofepris.total + legal.total;
        const filledDocs = cofepris.filled + legal.filled;
        const steps = this.stepPanels.length || 4;
        const stepPct = Math.round(((activeIndex + 1) / steps) * 25);
        const docPct = totalDocs ? Math.round((filledDocs / totalDocs) * 67) : 0;
        let pct = Math.max(stepPct, Math.min(100, 25 + docPct));
        if (privacy && activeIndex === steps - 1) pct = 100;
        const width = `${pct}%`;
        this.progressBars.forEach((bar) => bar.style.setProperty("--md-wizard-progress", width));
        if (this.progressPctEl) this.progressPctEl.textContent = width;
    },

    _showStep(targetIndex, opts) {
        const moved = this._super(targetIndex, opts);
        this._refreshAffiliacion();
        return moved;
    },

    // ── Submit ─────────────────────────────────────────────────────────────────
    _onSubmit(ev) {
        const activeIndex = this._getActiveStepIndex();
        if (activeIndex < this.stepPanels.length - 1) {
            ev.preventDefault();
            this._showStep(activeIndex + 1);
            return;
        }
        if (!this.form.reportValidity()) {
            ev.preventDefault();
            return;
        }
        ev.preventDefault();
        this._setBusy('<span class="spin"></span>Enviando…');
        fetch("/afiliacion", {
            method: "POST",
            body: new FormData(this.form),
        })
            .then((r) => r.json().catch(() => ({})).then((p) => ({ ok: r.ok, payload: p })))
            .then((data) => {
                if (!data || !data.ok || !data.payload || !data.payload.success) {
                    const message =
                        (data && data.payload && data.payload.message) ||
                        "No se pudo procesar tu solicitud. Verifica la información e inténtalo de nuevo.";
                    this._setIdle();
                    this._showError(message);
                    return;
                }
                this._showSuccess("Solicitud enviada");
            })
            .catch(() => {
                this._setIdle();
                this._showError("Error de conexión. Por favor intenta de nuevo.");
            });
    },
});

export default publicWidget.registry.MedicineDepotAfiliacionForm;
