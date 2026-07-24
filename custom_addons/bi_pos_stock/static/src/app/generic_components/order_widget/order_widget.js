/** @odoo-module */
/**
 * OrderDisplay extension — Total de Productos y Piezas (XML-only, ver order_widget.xml).
 *
 * FIXED (Odoo 19): OrderDisplay is "service-less": it receives the order via
 * props.order and does NOT use the POS store. All calculations for esa parte
 * se hacen en el template usando props.order.lines, sin patch de JS.
 *
 * Fusión visual de lotes en el ticket (mergeReceiptLotLines)
 * ─────────────────────────────────────────────────────────
 * Cuando el mismo producto (mismo price_unit y discount) queda repartido en
 * varias pos.order.line por llevar lotes distintos, orderline_lot_patch.js
 * las mantiene A PROPÓSITO como líneas separadas (para no perder trazabilidad
 * de inventario/reportes al fusionarlas). Este patch NO toca esa decisión ni
 * order.lines/pos.order.line: solo fusiona visualmente el DOM ya renderizado
 * del ticket impreso (mode === "receipt"), sumando qty/precio con los valores
 * YA calculados por Odoo (line.qty, line.displayPrice — motor de impuestos y
 * descuentos real, no una reimplementación propia) y moviendo los <li
 * class="lot-number"> de las líneas siguientes hacia la primera.
 *
 * Cada "Lote X" ya trae SU PROPIA cantidad de fábrica (lot_label_patch.js
 * incluye la cantidad de la línea de origen al construir el texto del lote,
 * formato "<cantidad> Lote <código> <fecha de caducidad>") — esta función solo
 * mueve esos <li class="lot-number"> ya formateados hacia la primera línea, sin
 * tocar su texto.
 *
 * Depende de data-merge-key/data-line-qty/data-line-price agregados vía XPath
 * sobre point_of_sale.Orderline (bi_pos_stock.OrderlineReceiptMergeAttrs).
 * Cualquier fallo se atrapa y se ignora: en el peor caso el ticket queda como
 * antes (líneas separadas), nunca rompe el render.
 */

import { patch } from "@web/core/utils/patch";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { useEffect } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { formatQty } from "../../utils/lot_expiry_utils";

patch(OrderDisplay.prototype, {
    setup() {
        super.setup();
        if (this.props.mode === "receipt") {
            useEffect(
                () => this.mergeReceiptLotLines(),
                () => [this.order.lines.length]
            );
        }
    },

    mergeReceiptLotLines() {
        try {
            const container = this.scrollableRef?.el;
            if (!container) {
                return;
            }

            const orderlineEls = Array.from(
                container.querySelectorAll(":scope > li.orderline[data-merge-key]")
            );
            const groups = new Map();
            for (const el of orderlineEls) {
                const key = el.dataset.mergeKey;
                if (!groups.has(key)) {
                    groups.set(key, []);
                }
                groups.get(key).push(el);
            }

            for (const group of groups.values()) {
                if (group.length < 2) {
                    continue;
                }
                const [first, ...rest] = group;

                // Solo fusiona si hay lotes que mostrar — dos renglones del mismo
                // producto sin lote no ganan nada al fusionarse.
                if (!first.querySelector(".lot-number")) {
                    continue;
                }
                const lotTarget = first.querySelector(".info-list .col.ps-0, .info-list");
                if (!lotTarget) {
                    continue;
                }

                let qtySum = 0;
                let priceSum = 0;
                for (const el of group) {
                    qtySum += parseFloat(el.dataset.lineQty || "0");
                    priceSum += parseFloat(el.dataset.linePrice || "0");
                }

                const qtyEl = first.querySelector(".qty");
                if (qtyEl) {
                    qtyEl.textContent = formatQty(qtySum);
                }
                const priceEl = first.querySelector(".product-price");
                if (priceEl) {
                    priceEl.textContent = formatCurrency(priceSum, this.order.currency.id);
                }

                for (const el of rest) {
                    el.querySelectorAll(".lot-number").forEach((lotEl) => {
                        lotTarget.appendChild(lotEl);
                    });
                    el.remove();
                }
            }
        } catch (err) {
            console.warn("[bi_pos_stock] mergeReceiptLotLines: fusión omitida por error", err);
        }
    },
});
