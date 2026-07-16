/** @odoo-module **/
// Medicine Depot · Portal Bento — patch robusto de PortalHomeCounters.
//
// La Interaction nativa @portal/interactions/portal_home_counters busca
// [data-placeholder_count] dentro de .o_portal_my_home, hace RPC a
// /my/counters y luego itera Object.keys(response) reasignando textContent
// SIN guard. Si el backend devuelve un counter cuyo elemento no esta en
// el DOM (escenario habitual cuando se reemplaza el layout estandar por
// uno custom como el Bento), querySelector retorna null y rompe la
// cadena de public.interactions de la pagina.
//
// Reimplementamos updateCounters con la misma logica que el original,
// pero con guards en cada querySelector. Asi el motor nativo opera
// transparentemente sobre los decoys [data-placeholder_count] del layout
// Bento y, si llega un counter inesperado, lo ignora silenciosamente.

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { PortalHomeCounters } from "@portal/interactions/portal_home_counters";

patch(PortalHomeCounters.prototype, {
    async updateCounters() {
        const counterEls = [
            ...this.el.querySelectorAll("[data-placeholder_count]"),
        ];
        const removeSpinner = () => {
            const spinner = this.el.querySelector(".o_portal_doc_spinner");
            if (spinner) {
                spinner.remove();
            }
        };

        if (!counterEls.length) {
            removeSpinner();
            return;
        }

        const needed = counterEls.map(
            (el) => el.dataset["placeholder_count"]
        );
        const numberRpc = Math.min(Math.ceil(needed.length / 5), 3);
        const counterByRpc = Math.ceil(needed.length / numberRpc);
        const countersAlwaysDisplayed = this.getCountersAlwaysDisplayed();

        const proms = [
            ...Array(Math.min(numberRpc, needed.length)).keys(),
        ].map(async (i) => {
            const slice = needed.slice(
                i * counterByRpc,
                (i + 1) * counterByRpc
            );
            const data = await rpc("/my/counters", { counters: slice });
            Object.keys(data).forEach((counterName) => {
                const counterEl = this.el.querySelector(
                    `[data-placeholder_count='${counterName}']`
                );
                if (!counterEl) {
                    return;
                }
                counterEl.textContent = data[counterName];
                if (
                    data[counterName] !== 0 ||
                    countersAlwaysDisplayed.includes(counterName)
                ) {
                    const card = counterEl.closest(".o_portal_index_card");
                    if (card) {
                        card.classList.remove("d-none");
                    }
                }
            });
            return data;
        });

        try {
            await Promise.all(proms);
        } catch (e) {
            // Wrap non-Error rejections: rpc() can reject with plain objects on
            // network failures, causing Odoo's formatTraceback to crash on
            // error.stack.split('\n') when the value has no .stack property.
            const wrapped = e instanceof Error ? e : new Error(String(e ?? 'RPC counters failed'));
            console.warn('[MD] Portal counters: non-critical update failure —', wrapped.message);
            // Do not re-throw: counter display is decorative, page must not break.
        } finally {
            removeSpinner();
        }
    },
});
