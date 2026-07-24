/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * MdWizardBase — lógica común de wizard multi-paso para formularios del portal.
 *
 * Subclases deben sobreescribir las propiedades de configuración y los event
 * handlers específicos (submit URL, IDs de elementos). Métodos comunes de
 * stepper, validación y progreso se heredan sin duplicación.
 *
 * Propiedades de configuración (sobreescribir en la subclase):
 *   _stepAttr        — selector de los paneles de paso (ej. "[data-aff-step]")
 *   _stepTriggerAttr — selector de los triggers de salto (ej. "[data-aff-step-jump]")
 *   _stepJumpDataKey — clave de dataset del trigger (ej. "affStepJump")
 *   _submitBtnSel    — selector del botón de envío
 *   _successScreenSel — selector de la pantalla de éxito
 *   _errorBoxSel     — selector del cuadro de error
 */
const MdWizardBase = publicWidget.Widget.extend({

    // ── Configuración (sobreescribir en subclase) ─────────────────────────────
    _stepAttr:         "[data-wizard-step]",
    _stepTriggerAttr:  "[data-wizard-step-jump]",
    _stepJumpDataKey:  "wizardStepJump",
    _submitBtnSel:     "#wizard_submit_btn",
    _successScreenSel: "#wizard_success_screen",
    _errorBoxSel:      "#wizard_error_box",

    // ── Ciclo de vida ─────────────────────────────────────────────────────────
    start() {
        const form = this.el;
        this.form = form;
        this.submitBtn      = form.querySelector(this._submitBtnSel);
        this.successScreen  = form.querySelector(this._successScreenSel);
        this.errorBox       = form.querySelector(this._errorBoxSel);
        this.stepPanels     = Array.from(form.querySelectorAll(this._stepAttr));
        this.stepTriggers   = Array.from(form.querySelectorAll(this._stepTriggerAttr));
        this.progressBars   = Array.from(form.querySelectorAll("[data-wizard-progress-bar]"));
        this.submitLabel    = this.submitBtn ? this.submitBtn.innerHTML : "";
        if (this.stepPanels.length) {
            this._updateStepper(this._getActiveStepIndex());
        }
        return this._super(...arguments);
    },

    // ── Helpers de paso ───────────────────────────────────────────────────────
    _getActiveStepIndex() {
        const i = this.stepPanels.findIndex((p) => p.classList.contains("is-active"));
        return i >= 0 ? i : 0;
    },

    _validateStep(stepIndex) {
        const step = this.stepPanels[stepIndex];
        if (!step) return true;
        const controls = Array.from(step.querySelectorAll("input, select, textarea")).filter(
            (c) => !c.disabled && c.type !== "hidden"
        );
        for (const control of controls) {
            if (typeof control.checkValidity === "function" && !control.checkValidity()) {
                if (typeof control.reportValidity === "function") control.reportValidity();
                control.focus({ preventScroll: false });
                return false;
            }
        }
        return true;
    },

    _validateStepsThrough(stepIndex) {
        for (let i = 0; i <= stepIndex; i += 1) {
            if (!this._validateStep(i)) return false;
        }
        return true;
    },

    _updateStepper(activeIndex) {
        const jumpKey = this._stepJumpDataKey;
        this.stepPanels.forEach((panel, index) => {
            panel.classList.toggle("is-active", index === activeIndex);
            panel.classList.toggle("is-complete", index < activeIndex);
            panel.setAttribute("aria-hidden", index === activeIndex ? "false" : "true");
        });
        this.stepTriggers.forEach((trigger) => {
            const target = parseInt(trigger.dataset[jumpKey] || "1", 10) - 1;
            const isActive = target === activeIndex;
            const isComplete = target < activeIndex;
            trigger.classList.toggle("is-active", isActive);
            trigger.classList.toggle("is-complete", isComplete);
            trigger.setAttribute("aria-current", isActive ? "step" : "false");
        });
        if (this.submitBtn) {
            this.submitBtn.disabled = activeIndex !== this.stepPanels.length - 1;
        }
        this._updateProgress(activeIndex);
    },

    _updateProgress(activeIndex) {
        if (!this.progressBars.length || !this.stepPanels.length) return;
        const ratio = ((activeIndex + 1) / this.stepPanels.length) * 100;
        const width = `${Math.min(100, Math.max(0, ratio)).toFixed(2)}%`;
        this.progressBars.forEach((bar) => bar.style.setProperty("--md-wizard-progress", width));
    },

    _showStep(targetIndex, { validateCurrent = true } = {}) {
        const currentIndex = this._getActiveStepIndex();
        if (targetIndex < 0 || targetIndex >= this.stepPanels.length) return false;
        if (targetIndex > currentIndex && validateCurrent && !this._validateStep(currentIndex)) {
            return false;
        }
        this._updateStepper(targetIndex);
        this.stepPanels[targetIndex].scrollIntoView({ behavior: "smooth", block: "start" });
        return true;
    },

    // ── Handlers de navegación (comunes) ─────────────────────────────────────
    _onNext(ev) {
        ev.preventDefault();
        this._showStep(this._getActiveStepIndex() + 1);
    },

    _onBack(ev) {
        ev.preventDefault();
        this._showStep(this._getActiveStepIndex() - 1, { validateCurrent: false });
    },

    _onJump(ev) {
        ev.preventDefault();
        const target = parseInt(ev.currentTarget.dataset[this._stepJumpDataKey] || "1", 10) - 1;
        const current = this._getActiveStepIndex();
        if (target <= current) {
            this._showStep(target, { validateCurrent: false });
            return;
        }
        if (this._validateStepsThrough(target - 1)) {
            this._showStep(target, { validateCurrent: false });
        }
    },

    // ── Helpers de estado de envío ────────────────────────────────────────────
    _setBusy(label) {
        if (this.errorBox) {
            this.errorBox.classList.add("d-none");
            this.errorBox.textContent = "";
        }
        if (this.submitBtn) {
            this.submitBtn.disabled = true;
            this.submitBtn.setAttribute("aria-busy", "true");
            this.submitBtn.innerHTML = label || '<span class="spin"></span>Enviando…';
        }
    },

    _setIdle() {
        if (this.submitBtn) {
            this.submitBtn.disabled = false;
            this.submitBtn.removeAttribute("aria-busy");
            this.submitBtn.innerHTML = this.submitLabel;
        }
    },

    _showError(message) {
        if (this.errorBox) {
            this.errorBox.textContent = message || "Error de conexión. Por favor intenta de nuevo.";
            this.errorBox.classList.remove("d-none");
        }
    },

    _showSuccess(label) {
        if (this.successScreen) this.successScreen.classList.remove("d-none");
        if (this.submitBtn) {
            this.submitBtn.removeAttribute("aria-busy");
            this.submitBtn.innerHTML = label || "Enviado";
        }
    },
});

export default MdWizardBase;
