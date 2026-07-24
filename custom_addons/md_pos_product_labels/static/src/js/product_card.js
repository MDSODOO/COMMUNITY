/** @odoo-module */
/**
 * ProductCard extension -- identificacion regulatoria completa (COFEPRIS).
 *
 * Agrega:
 *   1. get substanceBadges()      -- hasta 2 tags de sustancia activa +
 *                                     un chip "+N" si hay mas, coloreados
 *                                     con el campo "color" de
 *                                     md.active.substance (mismo criterio
 *                                     que el widget many2many_tags del
 *                                     kanban de Inventario en
 *                                     md_pharma_regulatory).
 *   2. get hasRegulatoryDetail()  -- true si hay algo que valga la pena
 *                                     mostrar en el popup de detalle
 *                                     (evita mostrar el boton (i) en
 *                                     productos sin ningun dato
 *                                     regulatorio capturado, ej. articulos
 *                                     generales sin homologar todavia).
 *   3. openRegulatoryDetail()     -- abre RegulatoryDetailPopup.
 *
 * Por que un popup y no mas badges en la card (decision de UX):
 *   La card de POS ya trae hasta 5 badges regulatorios en una fila
 *   (forma/concentracion/contenido/envase/talla) + el badge de stock y el
 *   boton de lotes FEFO de bi_pos_stock. Sumar ademas linea/marca,
 *   registro sanitario, dimensiones y el nombre homologado propuesto como
 *   badges satura visualmente la card y la vuelve dificil de leer bajo
 *   presion (cajero atendiendo cliente). Se prioriza en la card SOLO lo
 *   que ayuda a diferenciar productos parecidos de un vistazo -- sustancia
 *   activa y talla, que son los que mas cambian la identidad real del
 *   producto -- y el resto queda a un tap de distancia, mismo patron que
 *   el boton (i) de lotes de bi_pos_stock (lot_detail_popup). Se separa
 *   visualmente del boton de lotes: el nuestro va en la esquina superior
 *   IZQUIERDA (vs. derecha) y en color teal solido (vs. blanco), para que
 *   nunca se confundan ni se superpongan.
 */

import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { RegulatoryDetailPopup } from "../components/regulatory_detail_popup/regulatory_detail_popup";
import { tagColorStyle } from "./color_utils";

const MAX_SUBSTANCE_BADGES = 2;

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.mdRegulatoryDialog = useService("dialog");
    },

    get substanceBadges() {
        const substances = this.props.product.active_substance_ids || [];
        const shown = substances.slice(0, MAX_SUBSTANCE_BADGES).map((s) => ({
            id: s.id,
            name: s.name,
            style: tagColorStyle(s.color),
        }));
        return { shown, extraCount: substances.length - shown.length };
    },

    get hasRegulatoryDetail() {
        const p = this.props.product;
        return !!(
            (p.active_substance_ids && p.active_substance_ids.length) ||
            p.product_line_id ||
            p.l10n_mx_registro_sanitario ||
            p.l10n_mx_requiere_receta ||
            p.l10n_mx_controlado ||
            p.l10n_mx_dimensiones ||
            p.l10n_mx_talla ||
            (p.l10n_mx_nombre_homologado && p.l10n_mx_homologacion_state !== "no_elegible")
        );
    },

    openRegulatoryDetail(event) {
        event?.stopPropagation();
        const product = this.props.product;
        if (!product?.id) {
            return;
        }
        this.mdRegulatoryDialog.add(RegulatoryDetailPopup, { product });
    },
});
