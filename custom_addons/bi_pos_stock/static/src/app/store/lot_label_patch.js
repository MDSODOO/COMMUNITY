/** @odoo-module */
/**
 * PosOrderline patch — formato "<cantidad> Lote <código> <fecha de caducidad>"
 * en vez del "Lot Number <código>" (sin cantidad ni fecha) que Odoo core
 * hardcodea en inglés en el getter `packLotLines`
 * (addons/point_of_sale/static/src/app/models/pos_order_line.js):
 *
 *   `${tracking == "lot" ? "Lot Number" : "SN"} ${lot_name}`
 *
 * No está envuelto en _t(), así que no hay .po que lo traduzca — hay que
 * sobreescribir el getter completo.
 *
 * Cantidad: orderline_lot_patch.js garantiza que cada pos.order.line lleva un
 * único lote (nunca fusiona líneas con lotes distintos), así que `this.qty` de
 * la línea ES la cantidad de ese lote — no hay que repartir nada aquí.
 *
 * Fecha de caducidad: no viene en pack_lot_ids: hay que buscarla en
 * pos.allLotDetails (precargado al abrir sesión por get_all_lot_details(), key
 * "{product_id}_{lot_name}") — ver lot_cascade_patch.js, misma fuente de datos.
 * PosOrderline no es un componente OWL (no puede usar usePos()), así que se
 * llega al PosStore activo vía getPosStoreRef() (models.js).
 *
 * order_widget.js (mergeReceiptLotLines) ya NO necesita anexar la cantidad al
 * fusionar líneas del mismo producto con lotes distintos: cada renglón trae su
 * propia cantidad de fábrica en este getter.
 */

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { getPosStoreRef } from "./models";
import { formatExpiryDate, formatQty } from "../utils/lot_expiry_utils";

patch(PosOrderline.prototype, {
    get packLotLines() {
        const pos = getPosStoreRef();
        const qtyLabel = formatQty(this.qty || 0);
        return this.pack_lot_ids.map((l) => {
            const prefix = l.pos_order_line_id.product_id.tracking == "lot" ? "Lote" : "NS";
            let expiryLabel = "";
            if (pos?.allLotDetails) {
                const detail = pos.allLotDetails[`${this.product_id.id}_${l.lot_name}`];
                if (detail?.expiration_date) {
                    expiryLabel = ` ${formatExpiryDate(detail.expiration_date)}`;
                }
            }
            return `${qtyLabel} ${prefix} ${l.lot_name}${expiryLabel}`;
        });
    },
});
