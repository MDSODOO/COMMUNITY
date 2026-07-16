/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.MdMedicdForm = publicWidget.Widget.extend({
    selector: '#medicd-form',
    events: {
        'change [name="tiene_farmacia"]': '_onFarmaciaChange',
        'change [name="tiene_proveedor"]': '_onProveedorChange',
        'submit': '_onSubmit',
    },

    start() {
        this._super(...arguments);
        this._fieldsSi = this.el.querySelector('#medicd-fields-si');
        this._fieldsNo = this.el.querySelector('#medicd-fields-no');
        this._fieldProveedor = this.el.querySelector('#medicd-field-proveedor');
        this._msg = this.el.querySelector('#medicd-msg');
        this._submitBtn = this.el.querySelector('#medicd-submit-btn');
    },

    _onFarmaciaChange(ev) {
        const val = ev.target.value;
        this._fieldsSi.hidden = val !== 'si';
        this._fieldsNo.hidden = val !== 'no';
        if (val !== 'si') {
            this.el.querySelectorAll('[name="tiene_proveedor"]')
                .forEach(r => { r.checked = false; });
            this._fieldProveedor.hidden = true;
        }
    },

    _onProveedorChange(ev) {
        this._fieldProveedor.hidden = ev.target.value !== 'si';
    },

    async _onSubmit(ev) {
        ev.preventDefault();
        this._showMsg('', '');
        this._submitBtn.disabled = true;

        const data = new FormData(this.el);

        try {
            const res = await fetch(this.el.dataset.action, {
                method: 'POST',
                body: data,
            });
            const json = await res.json();
            if (json.success) {
                this._showMsg(json.message, 'is-success');
                this.el.reset();
                this._fieldsSi.hidden = true;
                this._fieldsNo.hidden = true;
                this._fieldProveedor.hidden = true;
            } else {
                this._showMsg(json.message || 'Error al enviar.', 'is-error');
            }
        } catch {
            this._showMsg('Error de red. Intenta de nuevo.', 'is-error');
        } finally {
            this._submitBtn.disabled = false;
        }
    },

    _showMsg(text, cls) {
        this._msg.textContent = text;
        this._msg.className = 'md_pv_hint';
        if (cls) this._msg.classList.add(cls);
        this._msg.hidden = !text;
    },
});

export default publicWidget.registry.MdMedicdForm;
