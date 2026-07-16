/** @odoo-module */
/**
 * RegulatoryDetailPopup -- ficha regulatoria completa de un producto
 * (homologacion COFEPRIS), abierta desde el boton (i) teal en la esquina
 * superior IZQUIERDA de la ProductCard (ver product_card.js en este mismo
 * modulo).
 *
 * A diferencia de bi_pos_stock.LotDetailPopup (boton (i) blanco, esquina
 * superior DERECHA, trae datos de lotes via RPC a pos.session), este
 * popup no hace ninguna llamada al servidor: todos los campos que
 * muestra ya viajan al POS dentro de product.template (ver
 * models/product_product.py), asi que solo lee props.product directo.
 * Mas rapido y no depende de conectividad en el momento de la venta.
 *
 * Props:
 *   product -- registro product.template (ya cargado en el store del POS)
 *   close   -- Function (inyectado por el servicio de dialogos)
 */
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { tagColorStyle } from "../../js/color_utils";

const HOMOLOGACION_LABELS = {
    propuesto: "Propuesto (pendiente de aprobación)",
    aprobado: "Aprobado",
    aplicado: "Aplicado",
};

export class RegulatoryDetailPopup extends Component {
    static template = "md_pos_product_labels.RegulatoryDetailPopup";
    static components = { Dialog };
    static props = {
        product: Object,
        close: Function,
    };

    get product() {
        return this.props.product;
    }

    get substances() {
        return (this.product.active_substance_ids || []).map((s) => ({
            id: s.id,
            name: s.name,
            style: tagColorStyle(s.color),
        }));
    }

    get homologacionLabel() {
        return HOMOLOGACION_LABELS[this.product.l10n_mx_homologacion_state] || null;
    }
}
