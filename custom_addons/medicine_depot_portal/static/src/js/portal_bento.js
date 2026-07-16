/** @odoo-module **/
// Medicine Depot · Portal Bento — micro-interacciones.

import publicWidget from "@web/legacy/js/public/public_widget";

// ─── Widget Bento (hover spotlight) ──────────────────────────────────
publicWidget.registry.MedicineDepotBento = publicWidget.Widget.extend({
    selector: ".md_bento_portal",
    events: {
        "mousemove .md_data_card": "_onCellHover",
        "mouseleave .md_data_card": "_onCellLeave",
    },

    _onCellHover(ev) {
        const cell = ev.currentTarget;
        const r = cell.getBoundingClientRect();
        cell.style.setProperty("--md-mx", `${((ev.clientX - r.left) / r.width) * 100}%`);
        cell.style.setProperty("--md-my", `${((ev.clientY - r.top) / r.height) * 100}%`);
    },

    _onCellLeave(ev) {
        ev.currentTarget.style.removeProperty("--md-mx");
        ev.currentTarget.style.removeProperty("--md-my");
    },
});

export default publicWidget.registry.MedicineDepotBento;
