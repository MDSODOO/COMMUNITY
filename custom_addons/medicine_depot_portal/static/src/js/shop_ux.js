/** @odoo-module **/
// Medicine Depot · Shop UX enhancements
// M15: Sticky add-to-cart bar (IntersectionObserver)
// M17: Quantity stepper +/−
// M8:  Free-shipping progress bar in offcanvas/cart header

import publicWidget from '@web/legacy/js/public/public_widget';

// ── Sticky Add-to-Cart Bar (M15) ──────────────────────────────────────────────
publicWidget.registry.MdStickyAtcBar = publicWidget.Widget.extend({
    selector: '.product_detail, #product_detail',
    disabledInEditableMode: true,

    start() {
        this._super(...arguments);
        const addBtn = document.getElementById('add_to_cart') ||
                       this.el.querySelector('.btn_add_to_cart, a[id="add_to_cart"]');
        if (!addBtn) return;

        this._bar = this._buildBar(addBtn);
        document.body.appendChild(this._bar);

        this._observer = new IntersectionObserver(
            ([entry]) => this._bar.classList.toggle('is-visible', !entry.isIntersecting),
            { threshold: 0 }
        );
        this._observer.observe(addBtn);

        this._bar.querySelector('.md-sticky-atc-btn')?.addEventListener('click', (ev) => {
            ev.preventDefault();
            addBtn.click();
        });
    },

    _buildBar(addBtn) {
        const bar = document.createElement('div');
        bar.className = 'md-sticky-atc-bar';
        bar.setAttribute('aria-live', 'polite');

        const name = document.querySelector(
            'h1.product_name, h1[itemprop="name"], .product_template_name'
        )?.textContent?.trim() || '';
        const priceEl = document.querySelector(
            '.product_price .oe_price .oe_currency_value, [itemprop="price"]'
        );
        const price = priceEl ? priceEl.closest('.oe_price, [itemprop="price"]')?.textContent?.trim() || '' : '';

        bar.innerHTML = `
            <span class="md-sticky-atc-name"></span>
            ${price ? `<span class="md-sticky-atc-price"></span>` : ''}
            <button class="md-sticky-atc-btn" type="button">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
                Añadir al carrito
            </button>`;
        bar.querySelector('.md-sticky-atc-name').textContent = name;
        if (price) bar.querySelector('.md-sticky-atc-price').textContent = price;
        return bar;
    },

    destroy() {
        this._observer?.disconnect();
        this._bar?.remove();
        this._super(...arguments);
    },
});

// ── Quantity Stepper (M17) ────────────────────────────────────────────────────
// Odoo 19 PDP quantity input lives in various containers depending on theme/version.
// We attach to the product_detail root and locate the input ourselves.
publicWidget.registry.MdQtyStepper = publicWidget.Widget.extend({
    selector: '.product_detail, #product_detail, .o_wsale_product_main_col',
    disabledInEditableMode: true,

    start() {
        this._super(...arguments);
        // Find quantity input: Odoo 17-19 uses different selectors
        const input = this.el.querySelector(
            'input[name="add_qty"], input.js_quantity, ' +
            '#product_quantity input, .css_quantity input, ' +
            '[data-field-name="add_qty"] input'
        );
        if (!input) return;
        if (input.closest('.md-qty-stepper')) return; // already injected
        const nativeQuantity = input.closest('.css_quantity');
        if (nativeQuantity?.querySelector('.js_add_cart_json, .css_quantity_minus, .css_quantity_plus')) {
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'md-qty-stepper';

        const minus = document.createElement('button');
        minus.type = 'button';
        minus.textContent = '−';
        minus.setAttribute('aria-label', 'Reducir cantidad');

        const plus = document.createElement('button');
        plus.type = 'button';
        plus.textContent = '+';
        plus.setAttribute('aria-label', 'Aumentar cantidad');

        // Wrap: insert wrapper before input, then move input inside
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(minus);
        wrapper.appendChild(input);
        wrapper.appendChild(plus);

        const getValue = () => Math.max(1, parseInt(input.value, 10) || 1);
        const setValue = (v) => {
            input.value = Math.max(1, Math.min(999, v));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            input.dispatchEvent(new Event('input',  { bubbles: true }));
        };

        minus.addEventListener('click', () => setValue(getValue() - 1));
        plus.addEventListener('click',  () => setValue(getValue() + 1));
    },
});

// ── Free-shipping progress indicator (M12) ───────────────────────────────────
publicWidget.registry.MdFreeShippingBar = publicWidget.Widget.extend({
    selector: '.o_cart_offcanvas, #cart_total, .o_website_sale_cart',
    disabledInEditableMode: true,

    start() {
        this._super(...arguments);
        const THRESHOLD = 3500; // MXN
        if (this.el.querySelector('.md-free-shipping-progress')) return;
        const totalEl = this.el.querySelector(
            '.js_cart_lines .oe_currency_value, #cart_total .oe_currency_value, ' +
            '.o_total_table .oe_currency_value'
        );
        if (!totalEl) return;

        const rawText = (totalEl.textContent || '0').replace(/[^0-9,.\-]/g, '');
        const normalized = rawText.includes(',') && rawText.includes('.')
            ? rawText.replace(/,/g, '')
            : rawText.replace(',', '.');
        const raw = parseFloat(normalized) || 0;
        const pct = Math.min(100, (raw / THRESHOLD) * 100);
        const remaining = Math.max(0, THRESHOLD - raw);

        const bar = document.createElement('div');
        bar.className = 'md-free-shipping-progress';
        bar.innerHTML = `
            <span>${pct >= 100
                ? '¡Envío gratis desbloqueado!'
                : `$${remaining.toLocaleString('es-MX')} más para envío gratis`
            }</span>
            <div class="md-free-shipping-bar-track">
                <div class="md-free-shipping-bar-fill" style="width:${pct}%"></div>
            </div>`;

        const header = this.el.querySelector('.offcanvas-header, .o_cart_offcanvas_header, thead');
        if (header) {
            header.insertAdjacentElement('afterend', bar);
        } else {
            this.el.prepend(bar);
        }
    },
});

// ── Sticky class toggle on shop sort bar ─────────────────────────────────────
publicWidget.registry.MdShopSortBarSticky = publicWidget.Widget.extend({
    selector: '.o_wsale_sort_bar, .o_wsale_products_topbar',
    disabledInEditableMode: true,

    start() {
        this._super(...arguments);
        const top = this.el.getBoundingClientRect().top + window.scrollY;
        const onScroll = () => {
            const isSticky = window.scrollY > top - 96;
            this.el.classList.toggle('is-sticky', isSticky);
        };
        this._onScroll = onScroll;
        window.addEventListener('scroll', this._onScroll, { passive: true });
        onScroll();
    },

    destroy() {
        if (this._onScroll) {
            window.removeEventListener('scroll', this._onScroll);
        }
        this._super(...arguments);
    },
});

export default {
    MdStickyAtcBar:     publicWidget.registry.MdStickyAtcBar,
    MdQtyStepper:       publicWidget.registry.MdQtyStepper,
    MdFreeShippingBar:  publicWidget.registry.MdFreeShippingBar,
    MdShopSortBarSticky: publicWidget.registry.MdShopSortBarSticky,
};
