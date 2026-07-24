/**
 * Fix: los filtros custom de la barra lateral (Ingrediente Activo, Línea,
 * Descuentos Especiales) no funcionaban — quedaban descartados en cada clic.
 *
 * Causa raíz (verificada contra el código fuente real de Odoo 19.0,
 * addons/website_sale/static/src/interactions/website_sale.js):
 * TODO input/select dentro de `form.js_attributes` dispara el listener
 * delegado `onChangeAttribute`, que reconstruye la URL desde cero usando
 * SOLO los inputs con name="attribute_value" o name="tags" — cualquier otro
 * filtro (active_ingredient, product_line, discount_tier) se lee pero se
 * descarta en silencio, y `redirect()` navega inmediatamente a esa URL
 * incompleta. El `onchange="this.form.requestSubmit()"` inline que estos
 * filtros usaban entra en carrera con ese listener nativo y siempre pierde
 * (por eso se quitó de los templates — ver custom_shop_qty_selector/views/
 * templates.xml).
 *
 * Fix: parchear onChangeAttribute para que también agregue estos 3 filtros
 * a la URL, con semántica de parámetro repetido (?active_ingredient=1&
 * active_ingredient=2), igual que espera el backend
 * (request.httprequest.args.getlist(...) en controllers/main.py) — NO la
 * semántica de valor único separado por comas que usa attribute_values/tags.
 */
import { patch } from "@web/core/utils/patch";
import { redirect } from "@web/core/utils/urls";
import { WebsiteSale } from "@website_sale/interactions/website_sale";
import wSaleUtils from "@website_sale/js/website_sale_utils";

const MD_CUSTOM_FILTER_NAMES = ["active_ingredient", "product_line", "discount_tier"];

patch(WebsiteSale.prototype, {
    onChangeAttribute(ev) {
        const productGrid = this.el.querySelector(".o_wsale_products_grid_table_wrapper");
        if (productGrid) {
            productGrid.classList.add("opacity-50");
        }
        const form = wSaleUtils.getClosestProductForm(ev.currentTarget);
        const filters = form.querySelectorAll("input:checked, select");
        const attributeValues = new Map();
        const tags = new Set();
        const customFilters = new Map();
        for (const filter of filters) {
            if (!filter.value) {
                continue;
            }
            if (filter.name === "attribute_value") {
                const [attributeId, attributeValueId] = filter.value.split("-");
                const valueIds = attributeValues.get(attributeId) ?? new Set();
                valueIds.add(attributeValueId);
                attributeValues.set(attributeId, valueIds);
            } else if (filter.name === "tags") {
                tags.add(filter.value);
            } else if (MD_CUSTOM_FILTER_NAMES.includes(filter.name)) {
                const values = customFilters.get(filter.name) ?? new Set();
                values.add(filter.value);
                customFilters.set(filter.name, values);
            }
        }
        const url = new URL(form.action);
        const searchParams = url.searchParams;
        for (const entry of attributeValues.entries()) {
            searchParams.append("attribute_values", `${entry[0]}-${[...entry[1]].join(",")}`);
        }
        if (tags.size) {
            searchParams.set("tags", [...tags].join(","));
        }
        for (const [name, values] of customFilters.entries()) {
            for (const value of values) {
                searchParams.append(name, value);
            }
        }
        redirect(`${url.pathname}?${searchParams.toString()}`);
    },
});
