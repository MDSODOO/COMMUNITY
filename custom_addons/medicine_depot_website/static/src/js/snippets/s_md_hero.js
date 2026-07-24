/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.MdHeroSlider = publicWidget.Widget.extend({
    selector: '.s_md_hero[data-hero-slider],.s_md_hero',
    disabledInEditableMode: false,

    start() {
        this._super(...arguments);
        const slider = this.el.querySelector('[data-hero-slider]');
        if (!slider) return;

        this._slider = slider;
        this._allSlides = [...slider.querySelectorAll('.s_md_hero-slide')];
        this._allDots = [...this.el.querySelectorAll('[data-hero-dots] .s_md_hero-dot')];
        this._pauseButton = this.el.querySelector('[data-hero-pause]');
        this._isPaused = false;
        this._prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches || false;
        this._manualPaused = this._prefersReducedMotion;
        this._interactionPaused = false;
        this._current = 0;

        this._expireCampaignSlides();
        this._slides = this._allSlides.filter((slide) => !slide.hidden);
        this._dots = this._allDots.filter((dot, i) => {
            const isVisible = Boolean(this._slides[i]);
            dot.hidden = !isVisible;
            return isVisible;
        });

        this._allSlides.forEach((slide) => slide.classList.remove('is-active'));
        this._allDots.forEach((dot) => dot.classList.remove('is-active'));
        this._slides[0]?.classList.add('is-active');
        this._dots[0]?.classList.add('is-active');
        this._syncA11y();

        if (this._slides.length <= 1) {
            this.el.querySelector('[data-hero-controls]')?.setAttribute('hidden', 'hidden');
            return;
        }

        this._boundPause = () => {
            this._interactionPaused = true;
            this._syncPausedState();
        };
        this._boundResume = () => {
            this._interactionPaused = false;
            this._syncPausedState();
        };
        this._boundVisibility = () => {
            this._syncPausedState();
        };

        this.el.addEventListener('mouseenter', this._boundPause);
        this.el.addEventListener('mouseleave', this._boundResume);
        this.el.addEventListener('focusin', this._boundPause);
        this.el.addEventListener('focusout', this._boundResume);
        document.addEventListener('visibilitychange', this._boundVisibility);

        if (this._slides.length > 1) {
            this._syncPausedState();
            this._dots.forEach((dot, i) => {
                dot.addEventListener('click', () => this._goTo(i));
            });
            if (this._prefersReducedMotion && this._pauseButton) {
                this._pauseButton.setAttribute('aria-pressed', 'true');
                this._pauseButton.textContent = 'Reanudar';
            }
            this._pauseButton?.addEventListener('click', () => {
                this._manualPaused = !this._manualPaused;
                this._pauseButton.setAttribute('aria-pressed', this._manualPaused ? 'true' : 'false');
                this._pauseButton.textContent = this._manualPaused ? 'Reanudar' : 'Pausar';
                this._syncPausedState();
            });
        }
    },

    destroy() {
        this._stopTimer();
        if (this._boundPause) {
            this.el.removeEventListener('mouseenter', this._boundPause);
            this.el.removeEventListener('focusin', this._boundPause);
        }
        if (this._boundResume) {
            this.el.removeEventListener('mouseleave', this._boundResume);
            this.el.removeEventListener('focusout', this._boundResume);
        }
        if (this._boundVisibility) {
            document.removeEventListener('visibilitychange', this._boundVisibility);
        }
        this._super(...arguments);
    },

    _expireCampaignSlides() {
        const today = new Date();
        this._allSlides.forEach((slide) => {
            const end = slide.dataset.campaignEnd;
            if (!end) return;

            const endDate = new Date(`${end}T00:00:00`);
            if (!Number.isNaN(endDate.getTime()) && today >= endDate) {
                slide.hidden = true;
            }
        });
    },

    _startTimer() {
        this._stopTimer();
        this._interval = setInterval(() => this._advance(), 6500);
    },

    _stopTimer() {
        clearInterval(this._interval);
        this._interval = null;
    },

    _syncPausedState() {
        this._setPaused(this._manualPaused || this._interactionPaused || document.hidden);
    },

    _setPaused(paused) {
        this._isPaused = paused;
        if (paused) {
            this._stopTimer();
        } else {
            this._startTimer();
        }
    },

    _advance() {
        this._goTo((this._current + 1) % this._slides.length);
    },

    _goTo(idx) {
        if (!this._slides.length || idx === this._current) return;

        this._slides[this._current].classList.remove('is-active');
        this._dots[this._current]?.classList.remove('is-active');
        this._current = idx;
        this._slides[this._current].classList.add('is-active');
        this._dots[this._current]?.classList.add('is-active');
        this._syncA11y();
    },

    _syncA11y() {
        this._allSlides?.forEach((slide) => {
            slide.setAttribute('aria-hidden', slide.classList.contains('is-active') ? 'false' : 'true');
        });
        this._allDots?.forEach((dot) => dot.removeAttribute('aria-current'));
        this._dots?.[this._current]?.setAttribute('aria-current', 'true');
    },
});

export default publicWidget.registry.MdHeroSlider;
