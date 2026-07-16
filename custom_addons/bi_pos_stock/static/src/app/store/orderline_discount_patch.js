/** @odoo-module */
/**
 * PosOrderline patch — "efectivo" % de descuento visible para líneas con precio
 * rebajado por pricelist, no solo por numpad.
 *
 * Verificado en el bundle real de Odoo 19 (point_of_sale.assets_prod.min.js,
 * ProductProduct.getPrice()): cuando una regla de product.pricelist.item reduce
 * el precio de un producto (compute_price='percentage', 'fixed', o la rama de
 * fórmula con price_discount), el resultado se aplica DIRECTO sobre price_unit —
 * el campo `discount` de la línea nunca se toca. `discount` solo lo llena
 * setDiscount(), disparado por el numpad del cajero.
 *
 * Consecuencia: el badge nativo de Odoo (.price-per-unit, "X% off") y nuestro
 * propio bi_pos_stock.OrderlineInlineDiscount (order_widget.xml) — ambos
 * condicionados a `line.discount > 0` — nunca se mostraban para descuentos por
 * pricelist, aunque el precio cobrado sí fuera el correcto. Ver
 * docs/audits/2026-07-02_pricelist_discount_architecture.md §4d.
 *
 * Este patch NO cambia cómo Odoo calcula precios — solo agrega un getter que,
 * cuando discount===0 pero price_unit ya viene por debajo del lst_price real
 * del producto, deriva el % implícito comparando ambos. order_widget.xml usa
 * este getter en vez de leer line.discount directamente.
 */

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    /**
     * @returns {{ pct: number, originalUnitPrice: number }}
     *   pct: % de descuento a mostrar (0 si no hay ninguno detectable).
     *   originalUnitPrice: precio unitario ANTES del descuento, para el "$Y" del badge.
     */
    getEffectiveDiscountInfo() {
        if (this.discount > 0) {
            // Descuento manual (numpad): price_unit ya es el precio SIN descontar,
            // discount trae el % — comportamiento nativo, sin cambios.
            return { pct: this.discount, originalUnitPrice: this.price_unit };
        }

        const listPrice = this.product_id?.lst_price || 0;
        if (listPrice > 0 && this.price_unit < listPrice) {
            const pct = (1 - this.price_unit / listPrice) * 100;
            return { pct, originalUnitPrice: listPrice };
        }

        return { pct: 0, originalUnitPrice: this.price_unit };
    },
});
