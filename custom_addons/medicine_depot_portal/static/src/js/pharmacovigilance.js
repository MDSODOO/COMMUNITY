/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import MdWizardBase from "./md_wizard_base";

publicWidget.registry.MedicineDepotPharmacovigilanceForm = MdWizardBase.extend({
    selector: "#pharmacovigilance_form",

    // ── Configuración específica ───────────────────────────────────────────────
    _stepAttr:         "[data-pv-step]",
    _stepTriggerAttr:  "[data-pv-step-jump]",
    _stepJumpDataKey:  "pvStepJump",
    _submitBtnSel:     "#pv_submit_btn",
    _successScreenSel: "#pharmacovigilance_success_screen",
    _errorBoxSel:      "#pharmacovigilance_error_box",

    events: {
        "click [data-pv-next]":       "_onNext",
        "click [data-pv-back]":       "_onBack",
        "click [data-pv-step-jump]":  "_onJump",
        "submit":                     "_onSubmit",
    },

    // ── Checklist & Stepper Sync ────────────────────────────────────────────────
    _updateStepper(activeIndex) {
        this._super(...arguments);
        const checklistItems = this.el.querySelectorAll(".md_pv_check_item");
        checklistItems.forEach((item, index) => {
            item.classList.toggle("is-done", index < activeIndex);
            item.classList.toggle("is-active", index === activeIndex);
        });
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
        fetch("/farmacovigilancia", {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest" },
            body: new FormData(this.form),
        })
            .then((r) => r.json().catch(() => ({})).then((p) => ({ ok: r.ok, payload: p })))
            .then((data) => {
                if (!data || !data.ok || !data.payload || !data.payload.success) {
                    const message =
                        (data && data.payload && data.payload.message) ||
                        "No se pudo procesar tu reporte. Verifica la información e inténtalo de nuevo.";
                    this._setIdle();
                    this._showError(message);
                    return;
                }
                this._showSuccess("Reporte enviado");
            })
            .catch(() => {
                this._setIdle();
                this._showError("Error de conexión. Por favor intenta de nuevo.");
            });
    },
});

export default publicWidget.registry.MedicineDepotPharmacovigilanceForm;
