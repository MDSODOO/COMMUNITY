/** @odoo-module */
/**
 * Paleta de colores estandar de Odoo para tags (ver
 * web/static/src/scss/secondary_variables.scss: $o-colors, 12 entradas,
 * indice 0 = "Sin color"). Se replica el valor hexadecimal base aqui en
 * vez de depender del bundle de "web": el bundle liviano de POS
 * (point_of_sale._assets_pos) no tiene garantizado incluir ese SCSS, y
 * usar las clases o_tag_color_N sin ese SCSS cargado dejaria los tags
 * sin color (texto y fondo iguales = invisible -- exactamente el bug ya
 * encontrado una vez con color=0 en md.active.substance, no lo repetimos
 * por otra via).
 *
 * El indice 0 (gris) es solo un fallback defensivo: md.active.substance
 * requiere color != 0 por diseno (ver models/active_substance.py).
 */
const TAG_COLOR_PALETTE = [
    "#a2a2a2", "#ee2d2d", "#dc8534", "#e8bb1d", "#5794dd", "#9f628f",
    "#db8865", "#41a9a2", "#304be0", "#ee2f8a", "#61c36e", "#9872e6",
];

/**
 * Blanco o negro segun la luminosidad del fondo (formula de luminancia
 * perceptual estandar), para que el texto del badge sea siempre legible
 * sin tener que hardcodear un color de texto distinto por cada entrada
 * de la paleta (algunos colores, como el amarillo/naranja, son
 * demasiado claros para texto blanco).
 */
function readableTextColor(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.6 ? "#1a1a1a" : "#ffffff";
}

/** Devuelve un string CSS "background:...; color:...;" listo para usar
 * en un t-att-style, a partir del indice numerico guardado en el campo
 * "color" (Integer) de md.active.substance. */
export function tagColorStyle(colorIndex) {
    const idx = Number.isInteger(colorIndex) ? colorIndex : 0;
    const bg = TAG_COLOR_PALETTE[((idx % TAG_COLOR_PALETTE.length) + TAG_COLOR_PALETTE.length) % TAG_COLOR_PALETTE.length];
    return `background:${bg}; color:${readableTextColor(bg)};`;
}
