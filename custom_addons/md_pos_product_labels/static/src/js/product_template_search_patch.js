/** @odoo-module */
/**
 * Refuerza el buscador de POS (campo "Buscar productos...") para que
 * encuentre productos por sus caracteristicas regulatorias -- sustancia
 * activa, forma, concentracion, contenido, envase, talla y linea/marca --
 * ademas de nombre/referencia/codigo de barras (que ya cubre el core).
 *
 * IMPORTANTE -- esto es SOLO indexacion para busqueda. No cambia que texto
 * se muestra como nombre del producto: esa es una decision de negocio
 * explicitamente diferida (ver l10n_mx_nombre_homologado en
 * md_pharma_regulatory, todavia en estado "propuesto" para 1183
 * productos, pendiente de aprobacion). El cajero sigue viendo el nombre
 * corto de siempre; solo gana la posibilidad de ENCONTRAR el producto
 * tecleando, por ejemplo, "500mg", "jaloma" o el nombre de una sustancia.
 *
 * Como funciona: ProductTemplate.searchString (ver
 * point_of_sale/static/src/app/models/product_template.js) es el string
 * normalizado (sin acentos/mayusculas, via @web/core/l10n/utils::normalize)
 * contra el que se compara la palabra de busqueda en
 * pos_store.js::getProductsBySearchWord. Ya incluye name/default_code/
 * barcode + el searchString de cada variante. Lo extendemos via patch()
 * llamando a super para no duplicar esa logica, y le agregamos nuestros
 * campos. Se re-normaliza el conjunto extendido para mantener el mismo
 * criterio de comparacion (sin acentos, minusculas) usado en el resto del
 * codebase.
 *
 * Nota tecnica: la propiedad original usa cacheValues("searchString", ...)
 * para memoizar; como aca definimos un getter nuevo que llama a super
 * (que si usa cacheValues), el resultado final tambien queda
 * indirectamente cacheado por esa llamada interna -- no hace falta
 * memoizar de nuevo aca, pero como concatenamos strings en cada acceso,
 * usamos nuestro propio cache liviano basado en el mismo helper del
 * modelo (cacheValues) para evitar recomputar en cada tecla.
 */

import { patch } from "@web/core/utils/patch";
import { normalize } from "@web/core/l10n/utils";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";

patch(ProductTemplate.prototype, {
    get searchString() {
        return this.cacheValues("mdRegulatorySearchString", () => {
            const base = super.searchString;

            const substanceNames = (this.active_substance_ids || []).map((s) => s.name || "");
            const extraFields = [
                this.l10n_mx_forma_farmaceutica,
                this.l10n_mx_concentracion,
                this.l10n_mx_contenido_empaque,
                this.l10n_mx_tipo_envase,
                this.l10n_mx_talla,
                this.product_line_id?.name,
                this.l10n_mx_nombre_homologado,
                ...substanceNames,
            ];

            const extraRaw = extraFields.filter(Boolean).join(" ");
            if (!extraRaw) {
                return base;
            }
            return base + " " + normalize(extraRaw);
        });
    },
});
