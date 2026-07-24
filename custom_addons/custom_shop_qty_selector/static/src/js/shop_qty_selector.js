/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

const MAX_QTY = 9999;
const EXACT_LABEL = _t("A la mano");
const LOW_STOCK_THRESHOLD = 10;  // umbral "pocas piezas" → pulso ambar
const CART_SUBMIT_LOCK_MS = 1800;
const CART_ACTION_FRAGMENT = "/shop/cart/update";
const CART_SUBMIT_SELECTOR = [
    "a#add_to_cart",
    "button#add_to_cart",
    ".btn_add_to_cart",
    ".o_add_to_cart_btn",
    "[data-md-qty-btn]",
    ".o_wsale_product_btn .a-submit",
    "a[href*='/shop/cart/update']",
    "button[formaction*='/shop/cart/update']",
].join(", ");

function _cartGuardScope(el) {
    return (
        el.closest("form, .oe_product_cart, #product_details, .o_md_cart_submit_guard")
        || el
    );
}

function _isCartForm(form) {
    if (!form) {
        return false;
    }
    const action = form.getAttribute("action") || "";
    return (
        action.includes(CART_ACTION_FRAGMENT)
        || !!form.querySelector(CART_SUBMIT_SELECTOR)
    );
}

function _findCartSubmitTarget(target) {
    if (!(target instanceof Element)) {
        return null;
    }
    const trigger = target.closest(CART_SUBMIT_SELECTOR);
    if (trigger) {
        return trigger;
    }
    const form = target.closest("form");
    return _isCartForm(form) ? form : null;
}

function _hasInvalidCustomQty(scope) {
    const qtyInput = scope.querySelector(".js_shop_qty_selector input[name='add_qty']");
    if (!qtyInput) {
        return false;
    }
    return (parseInt(qtyInput.value || "0", 10) || 0) < 1;
}

function _cartSubmitButtons(scope) {
    return scope.querySelectorAll(CART_SUBMIT_SELECTOR);
}

function _setCartSubmitting(scope, active) {
    _cartSubmitButtons(scope).forEach((button) => {
        button.classList.toggle("o_md_cart_submit_locked", active);
        if (active) {
            button.setAttribute("aria-busy", "true");
        } else {
            button.removeAttribute("aria-busy");
        }
        if (button.tagName === "BUTTON") {
            button.disabled = active;
        }
    });
}

function _ensureWishlistVisible(scope = document) {
    const selectors = [
        ".o_add_wishlist",
        "button.o_add_wishlist",
        "a.o_add_wishlist",
        "a[href*='/shop/wishlist']",
    ];
    scope.querySelectorAll(selectors.join(", ")).forEach((el) => {
        el.classList.remove("d-none", "disabled");
        el.removeAttribute("disabled");
        el.style.pointerEvents = "auto";
        el.style.visibility = "visible";
        if (el.style.display === "none") {
            el.style.display = "";
        }
    });
}

// ─────────────────────────────────────────────────────────────────────
//  _render A la mano badge
// ─────────────────────────────────────────────────────────────────────
function _renderAlaManoBadge(el, qty) {
    el.classList.remove(
        "o_sqty_loading", "o_sqty_in_stock", "o_sqty_out_stock", "o_sqty_stock_hidden"
    );

    // qty === null: ocultar el badge cuando no hay dato comercial.
    if (qty === null) {
        el.innerHTML = "";
        el.classList.add("o_sqty_stock_hidden");
        return;
    }

    const dot = `<span class="o_sqty_dot" aria-hidden="true"></span>`;

    // Con cantidad positiva: "A la mano: <n> pzs" (verde; ambar si quedan pocas).
    if (qty > 0) {
        el.classList.add("o_sqty_in_stock");
        if (qty <= LOW_STOCK_THRESHOLD) {
            el.classList.add("o_sqty_low");
        } else {
            el.classList.remove("o_sqty_low");
        }
        el.innerHTML =
            dot +
            `<span class="o_sqty_label">${EXACT_LABEL}:</span>` +
            `<span class="o_sqty_qty">${qty}</span>` +
            `<span class="o_sqty_unit">pzs</span>`;
        return;
    }
    el.classList.remove("o_sqty_low");

    // Con cantidad cero: conserva la etiqueta comercial exacta.
    el.classList.add("o_sqty_out_stock");
    el.innerHTML =
        dot +
        `<span class="o_sqty_label o_sqty_empty">${EXACT_LABEL}:</span>` +
        `<span class="o_sqty_qty o_sqty_empty">${qty}</span>` +
        `<span class="o_sqty_unit">pzs</span>`;
}


// ═════════════════════════════════════════════════════════════════════
//  CART SUBMIT GUARD  —  debounce click/submit bursts
// ═════════════════════════════════════════════════════════════════════
publicWidget.registry.ShopCartSubmitGuard = publicWidget.Widget.extend({
    selector: "body",

    start() {
        this._onClick = (ev) => this._guardEvent(ev, _findCartSubmitTarget(ev.target));
        this._onSubmit = (ev) => {
            const form = ev.target instanceof Element ? ev.target.closest("form") : null;
            this._guardEvent(ev, _isCartForm(form) ? form : null);
        };
        document.addEventListener("click", this._onClick, true);
        document.addEventListener("submit", this._onSubmit, true);
        return this._super(...arguments);
    },

    destroy() {
        document.removeEventListener("click", this._onClick, true);
        document.removeEventListener("submit", this._onSubmit, true);
        this._super(...arguments);
    },

    _guardEvent(ev, target) {
        if (!target) {
            return true;
        }
        const scope = _cartGuardScope(target);
        if (_hasInvalidCustomQty(scope)) {
            return true;
        }
        if (scope.dataset.mdCartSubmitLocked === "1") {
            ev.preventDefault();
            ev.stopImmediatePropagation();
            return false;
        }

        scope.dataset.mdCartSubmitLocked = "1";
        window.setTimeout(() => _setCartSubmitting(scope, true), 0);
        window.setTimeout(() => {
            delete scope.dataset.mdCartSubmitLocked;
            _setCartSubmitting(scope, false);
        }, CART_SUBMIT_LOCK_MS);
        return true;
    },
});


// ═════════════════════════════════════════════════════════════════════
//  SHOP GRID  —  ShopQtySelectorPage
// ═════════════════════════════════════════════════════════════════════
publicWidget.registry.ShopQtySelectorPage = publicWidget.Widget.extend({
    selector: "#products_grid, #products_grid_before, #o_comparelist_table",

    async start() {
        await this._super(...arguments);

        // Escopado a this.el: #products_grid, #products_grid_before y
        // #o_comparelist_table coexisten en el DOM y los 3 matchean este
        // widget -- sin escopar, cada instancia disparaba el mismo batch RPC
        // completo (confirmado: llamadas duplicadas a /shop/products/stock y
        // /shop/wishlist/get_product_ids en cada carga de /shop).
        const badgeEls   = this.el.querySelectorAll(".js_sqty_stock");
        const widgetEls  = this.el.querySelectorAll(".js_shop_qty_selector");

        // ── Product signals (batch RPC) ───────────────────────────────
        const productIds = [...badgeEls]
            .map((el) => parseInt(el.dataset.productId, 10))
            .filter(Boolean);

        const stockQtys = productIds.length
            ? await rpc("/shop/products/stock", { product_ids: productIds }).catch(() => ({}))
            : {};

        badgeEls.forEach((el) => {
            const qty = stockQtys[el.dataset.productId] ?? null;
            _renderAlaManoBadge(el, qty, true);

            // El badge puede vivir fuera del footer (overlay sobre la imagen en
            // el tema bento), asi que el CTA se busca desde la raiz de la card.
            const cta = el.closest(".oe_product_cart")?.querySelector(".o_sqty_cta_reveal");
            if (cta) {
                cta.classList.remove("o_sqty_cta_hidden", "o_sqty_cta_no_stock");
            }

            if (qty !== null && qty <= 0) {
                if (cta) {
                    // Mantener botón nativo; ocultar solo el selector custom.
                    cta.classList.add("o_sqty_cta_no_stock");
                }

                const card = el.closest(".oe_product_cart");
                if (card) _ensureWishlistVisible(card);
            }
        });

        // ── Qty widgets (solo para señales visibles) ──────────────────
        this._widgets = [];
        widgetEls.forEach((el) => {
            // No instanciar widget si el CTA ya fue ocultado.
            const cta = el.closest(".o_sqty_cta_reveal");
            if (cta?.classList.contains("o_sqty_cta_hidden") || cta?.classList.contains("o_sqty_cta_no_stock")) return;

            // "A la mano" ya resuelta por el batch RPC de arriba (stockQtys).
            // Sin dato (producto sin control de stock, o no vino en la
            // respuesta): fallback a MAX_QTY para no bloquear la venta.
            const onHandQty = stockQtys[el.dataset.productId];
            const maxQty = (typeof onHandQty === "number" && onHandQty >= 0) ? onHandQty : MAX_QTY;
            this._widgets.push(new ShopQtyWidget(el, maxQty));
        });
    },

    destroy() {
        (this._widgets || []).forEach((w) => w.destroy());
        this._super(...arguments);
    },
});


// ═════════════════════════════════════════════════════════════════════
//  PRODUCT DETAIL  —  ProductDetailAvailability
// ═════════════════════════════════════════════════════════════════════
publicWidget.registry.ProductDetailAvailability = publicWidget.Widget.extend({
    selector: ".js_sqty_detail_stock",

    async start() {
        this._lastId = parseInt(this.el.dataset.productId || "0", 10);
        const form   = this.el.closest("form") || document;
        this._input  = form.querySelector("input.product_id");

        if (this._input) {
            this._onChange = this._onChange.bind(this);
            this._input.addEventListener("change", this._onChange);
        }
        await this._super(...arguments);
        await this._refreshAvailability(true);
    },

    destroy() {
        this._input?.removeEventListener("change", this._onChange);
        this._super(...arguments);
    },

    async _onChange() {
        await this._refreshAvailability(false);
    },

    async _refreshAvailability(force = false) {
        const id = parseInt((this._input?.value || this.el.dataset.productId || "0"), 10);
        if (!id || (!force && id === this._lastId)) return;
        this._lastId = id;
        this.el.classList.add("o_sqty_loading");
        try {
            const { qty, is_storable } = await rpc("/shop/product/availability", { product_id: id });
            if (!is_storable) { this.el.classList.add("o_sqty_stock_hidden"); return; }
            this.el.classList.remove("o_sqty_stock_hidden");
            _renderAlaManoBadge(this.el, qty, false);
            if (qty <= 0) {
                const pdpRoot = this.el.closest("#product_details") || document;
                _ensureWishlistVisible(pdpRoot);
            }
        } catch {
            this.el.classList.remove("o_sqty_loading");
        }
    },
});


// ═════════════════════════════════════════════════════════════════════
//  FILTER SIDEBAR  —  active group highlighting + custom submit
//
//  El handler nativo de Odoo 19 (website_sale) sólo dispara el submit
//  del <form class="js_attributes"> cuando cambia un input con
//  name="attribute_value". Nuestros filtros custom (product_line,
//  active_ingredient) viven dentro del mismo form pero usan names
//  distintos → el handler nativo los ignora y el form no se envía.
//
//  Aquí: (a) destacamos el grupo activo con o_md_filter_group_active
//  y (b) forzamos form.requestSubmit() cuando cambia un input cuyo name
//  pertenece a nuestra whitelist de filtros custom.
//  requestSubmit() dispara el evento submit (a diferencia de submit()),
//  lo que permite que el handler nativo de Odoo procese la URL correctamente.
// ═════════════════════════════════════════════════════════════════════
const MD_CUSTOM_FILTER_NAMES = new Set(["product_line", "active_ingredient"]);

publicWidget.registry.ShopFilterState = publicWidget.Widget.extend({
    selector: ".js_attributes, #o_wsale_offcanvas_content",

    start() {
        this._onChange = this._onChange.bind(this);
        this.el.addEventListener("change", this._onChange);
        this.el.querySelectorAll(".form-check-input").forEach((input) => {
            this._refreshGroup(input);
        });
        return this._super(...arguments);
    },

    destroy() {
        this.el.removeEventListener("change", this._onChange);
        this._super(...arguments);
    },

    _onChange(ev) {
        const input = ev.target.closest(".form-check-input");
        if (!input) return;
        this._refreshGroup(input);

        if (input.name && MD_CUSTOM_FILTER_NAMES.has(input.name)) {
            const form = input.closest("form.js_attributes, form");
            if (form) {
                form.requestSubmit();
            }
        }
    },

    _refreshGroup(input) {
        const group = input.closest(".accordion-item, .nav-item");
        if (!group) return;

        const inputs = group.querySelectorAll(".form-check-input");
        group.classList.toggle(
            "o_md_filter_group_active",
            [...inputs].some((field) => field.checked),
        );
    },
});


// ═════════════════════════════════════════════════════════════════════
//  ShopQtyWidget  —  [ − | display | + | PZA ]
//
//  Renderiza el selector inline; sincroniza el input hidden add_qty
//  para que el form POST (y el interceptor JS de Odoo) reciban la
//  cantidad correcta sin necesidad de AJAX adicional.
// ═════════════════════════════════════════════════════════════════════
class ShopQtyWidget {
    constructor(container, maxQty = MAX_QTY) {
        this.el     = container;
        this.qty    = 0;
        this.maxQty = maxQty;
        this._render();
        this._bind();
        this._refresh();
    }

    _render() {
        // Estructura input-group nativa de Bootstrap 5: btn + form-control +
        // btn + input-group-text. flex-nowrap evita el wrap por defecto del
        // .input-group. La marca/branding se aplica desde el SCSS sin
        // sobrescribir el layout flex de BS.
        this.el.innerHTML = `
            <input type="hidden" name="add_qty" value="0"/>
            <div class="css_quantity input-group input-group-sm flex-nowrap align-items-stretch">
                <button class="sqty-minus btn btn-outline-secondary"
                        type="button" aria-label="Quitar uno">
                    <i class="oi oi-minus"></i>
                </button>
                <input type="number"
                       class="js_quantity sqty-display form-control text-center"
                       value="0" min="0" max="${this.maxQty}" step="1"
                       inputmode="numeric" aria-label="Cantidad"/>
                <button class="sqty-plus btn btn-outline-secondary"
                        type="button" aria-label="Agregar uno">
                    <i class="oi oi-plus"></i>
                </button>
                <span class="input-group-text o_sqty_unit">${_t("PZA")}</span>
            </div>`;

        this.$hidden  = this.el.querySelector("input[name='add_qty']");
        this.$minus   = this.el.querySelector(".sqty-minus");
        this.$display = this.el.querySelector(".sqty-display");
        this.$plus    = this.el.querySelector(".sqty-plus");
        this.$form    = this.el.closest("form");
    }

    _bind() {
        this._plus   = (e) => { e.preventDefault(); e.stopPropagation(); this._step(1);  };
        this._minus  = (e) => { e.preventDefault(); e.stopPropagation(); this._step(-1); };
        this._input  = (e) => this._onInput(e);
        this._blur   = ()  => this._refresh();
        this._submit = (e) => this._onSubmit(e);
        this.$plus.addEventListener("click",  this._plus);
        this.$minus.addEventListener("click", this._minus);
        this.$display.addEventListener("input",  this._input);
        this.$display.addEventListener("change", this._input);
        this.$display.addEventListener("blur",   this._blur);
        this.$form?.addEventListener("submit", this._submit);
    }

    _step(delta) {
        const next = this.qty + delta;
        if (next < 0 || next > this.maxQty) return;
        this.qty = next;
        this._refresh();
        this._bump();
    }

    // Item 30 · micro-animación de escala al incrementar/decrementar
    _bump() {
        if (!this.$display) return;
        this.$display.classList.remove("o_sqty_bump");
        // reflow para reiniciar la animación si se pulsa rápido
        void this.$display.offsetWidth;
        this.$display.classList.add("o_sqty_bump");
    }

    _onInput(e) {
        const raw = e.target.value;
        if (raw === "") { this.qty = 0; this._refresh(); return; }
        let n = parseInt(raw, 10);
        if (isNaN(n) || n < 0) n = 0;
        if (n > MAX_QTY) n = MAX_QTY;
        this.qty = n;
        this._refresh();
    }

    _onSubmit(e) {
        if (this.qty < 1 || this.qty > this.maxQty) {
            e.preventDefault();
            e.stopPropagation();
            this.$display.focus();
            this.$display.classList.add("o_sqty_invalid");
            setTimeout(() => this.$display.classList.remove("o_sqty_invalid"), 600);
        }
    }

    _toggleButtons() {
        this.$minus.disabled = this.qty <= 0;
        this.$minus.classList.toggle("disabled", this.qty <= 0);
        this.$plus.disabled  = this.qty >= this.maxQty;
    }

    _refresh() {
        this.$display.value = this.qty;
        this.$hidden.value  = this.qty;
        this._toggleButtons();
    }

    destroy() {
        this.$plus?.removeEventListener("click",  this._plus);
        this.$minus?.removeEventListener("click", this._minus);
        this.$display?.removeEventListener("input",  this._input);
        this.$display?.removeEventListener("change", this._input);
        this.$display?.removeEventListener("blur",   this._blur);
        this.$form?.removeEventListener("submit", this._submit);
        this.el.innerHTML = "";
    }
}

export default publicWidget.registry.ShopQtySelectorPage;
