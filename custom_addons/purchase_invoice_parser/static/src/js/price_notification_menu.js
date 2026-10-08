/** @odoo-module **/
import { Component, useState, useRef, reactive, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

const POLL_INTERVAL_MS = 30_000;

// Ventana de agrupacion de toasts. Una sola factura CFDI puede disparar
// decenas de cambios de precio casi simultaneos (un _sendone por linea): sin
// agrupar, el usuario recibe una avalancha de toasts apilados que tapan la
// pantalla y expiran en cascada. Se acumulan los eventos que llegan dentro de
// esta ventana y se emite UN solo toast resumen. 400ms es holgado frente al
// intervalo real entre mensajes del mismo lote (todos salen del mismo commit)
// y sigue siendo imperceptible como retraso.
const TOAST_BATCH_MS = 400;

// Duracion del toast efimero. Coincide con el default de notification_service
// (autocloseDelay=4000) pero se declara explicito porque es un requisito
// funcional, no una casualidad del framework.
const TOAST_DURATION_MS = 4000;

// Contador compartido de notificaciones sin leer.
//
// md_navbar_style consolida este boton dentro de su "Control Center" y oculta
// el trigger de la barra exterior (.pip_price_notification .o_nav_entry queda
// con opacity:0). Consecuencia: el badge del systray es correcto pero el
// usuario NO lo ve. Se publica el contador en un registry neutral para que
// quien muestre el boton pueda pintar su propia burbuja.
//
// Registry en vez de un import directo a propósito: invertir la dependencia
// (que purchase_invoice_parser importara md_navbar_style, o al reves) ataría
// un modulo de negocio a uno de tema. Aqui el productor no sabe quién
// consume, y el consumidor degrada a 0 si este modulo no está instalado.
export const priceNotificationCounter = reactive({ count: 0 });
registry.category("md_systray_counters").add("price_updates", priceNotificationCounter);

class PriceNotificationMenu extends Component {
    static template = "purchase_invoice_parser.PriceNotificationMenu";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.bus = useService("bus_service");
        this.action = useService("action");
        this.notification = useService("notification");

        // Referencia al <li> raiz. Sustituye a this.__owl__.bdom?.el, API
        // interna de OWL que en esta version NO resuelve: el cierre al hacer
        // click fuera nunca se disparaba (confirmado en vivo 2026-08-06,
        // incluso clickeando directamente el trigger nativo).
        this.rootRef = useRef("root");

        this.state = useState({
            visible: false,
            open: false,
            count: 0,
            notifications: [],
            loading: false,
        });

        this._boundClose = this._onDocumentClick.bind(this);
        this._pollTimer = null;
        this._toastBuffer = [];
        this._toastTimer = null;

        // Suscripción síncrona — antes de cualquier await para no perder eventos
        this.bus.subscribe(
            "purchase_invoice_parser/price_update",
            (payload) => this._onBusMessage(payload),
        );

        onMounted(async () => {
            // Ya no se hace addChannel(): el backend emite al canal de
            // registro res.partner de cada manager, y el servidor suscribe
            // esa sesion a su propio partner automaticamente
            // (bus/models/ir_websocket.py::_build_bus_channel_list). Pedir
            // aqui un canal string era justamente lo que abria el agujero:
            // el servidor acepta sin validar cualquier canal que mande el
            // cliente.
            await this._loadNotifications();
            if (this.state.visible) {
                this._pollTimer = setInterval(
                    () => this._loadNotifications(),
                    POLL_INTERVAL_MS,
                );
            }
            document.addEventListener("click", this._boundClose, true);
        });

        onWillUnmount(() => {
            if (this._pollTimer) {
                clearInterval(this._pollTimer);
                this._pollTimer = null;
            }
            if (this._toastTimer) {
                clearTimeout(this._toastTimer);
                this._toastTimer = null;
            }
            document.removeEventListener("click", this._boundClose, true);
        });
    }

    async _loadNotifications() {
        this.state.loading = true;
        try {
            const result = await this.orm.call(
                "purchase.price.notification",
                "get_unread",
                [],
            );
            this.state.count = result.count;
            this.state.notifications = result.notifications;
            this.state.visible = true;
            priceNotificationCounter.count = result.count;
        } catch {
            // Usuario sin grupo stock_manager: componente permanece oculto
        } finally {
            this.state.loading = false;
        }
    }

    _onBusMessage(payload) {
        if (!payload || !this.state.visible) return;
        if (payload.company_id !== user.activeCompany.id) {
            return;
        }
        // Evitar duplicados si el polling ya cargó la notificación
        const exists = this.state.notifications.some((n) => n.id === payload.id);
        if (!exists) {
            this.state.count += 1;
            this.state.notifications.unshift(payload);
            priceNotificationCounter.count = this.state.count;
            this._queueToast(payload);
        } else {
            const idx = this.state.notifications.findIndex((n) => n.id === payload.id);
            if (idx !== -1) {
                Object.assign(this.state.notifications[idx], payload);
                this.state.count = this.state.notifications.filter(
                    (n) => n.state === "unread"
                ).length;
                priceNotificationCounter.count = this.state.count;
            }
        }
    }

    // -- Toasts efimeros ---------------------------------------------------

    _queueToast(payload) {
        this._toastBuffer.push(payload);
        if (this._toastTimer) {
            clearTimeout(this._toastTimer);
        }
        this._toastTimer = setTimeout(() => this._flushToasts(), TOAST_BATCH_MS);
    }

    _flushToasts() {
        this._toastTimer = null;
        const batch = this._toastBuffer;
        this._toastBuffer = [];
        if (!batch.length) return;

        const ups = batch.filter((p) => p.direction === "up").length;
        const downs = batch.filter((p) => p.direction === "down").length;

        if (batch.length === 1) {
            const p = batch[0];
            const pct = p.delta_pct
                ? ` (${p.delta_pct > 0 ? "+" : ""}${p.delta_pct.toFixed(1)}%)`
                : "";
            this.notification.add(
                `${p.old_price_fmt} → ${p.new_price_fmt}${pct}\n${p.partner_name}`,
                {
                    title: p.product_name,
                    // Un costo de compra que SUBE es la mala noticia (erosiona
                    // margen) y por eso va en rojo; si baja, verde. Se invierte
                    // respecto al reflejo habitual de "verde = subir".
                    type: p.direction === "up" ? "danger" : "success",
                    autocloseDelay: TOAST_DURATION_MS,
                },
            );
            return;
        }

        const parts = [];
        if (ups) parts.push(`${ups} al alza`);
        if (downs) parts.push(`${downs} a la baja`);
        this.notification.add(
            `${parts.join(" · ")}. Abre el panel para revisarlas.`,
            {
                title: `${batch.length} actualizaciones de precio`,
                type: ups > downs ? "danger" : "success",
                autocloseDelay: TOAST_DURATION_MS,
            },
        );
    }

    // ----------------------------------------------------------------------

    _onDocumentClick(ev) {
        if (!this.state.open) return;
        const root = this.rootRef.el;
        if (root && !root.contains(ev.target)) {
            this.state.open = false;
        }
    }

    async toggle() {
        this.state.open = !this.state.open;
        if (this.state.open && this.state.count > 0) {
            await this._markAllRead();
        }
    }

    async _markAllRead() {
        try {
            await this.orm.call("purchase.price.notification", "mark_all_read", []);
            this.state.count = 0;
            priceNotificationCounter.count = 0;
            for (const n of this.state.notifications) {
                if (n.state === "unread") n.state = "read";
            }
        } catch {
            // silencioso
        }
    }

    goToProduct(tmplId) {
        if (!tmplId) return;
        this.state.open = false;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "product.template",
            res_id: tmplId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async applyPrice(notif) {
        if (notif.state === "applied" || notif._applying) return;
        notif._applying = true;
        try {
            const result = await this.orm.call(
                "purchase.price.notification",
                "apply_price_change",
                [notif.id],
            );
            if (result.applied || result.already_applied) {
                notif.state = "applied";
            }
        } catch {
            // silencioso — el usuario verá el mismo estado sin cambio
        } finally {
            notif._applying = false;
        }
    }

    async deleteNotification(notifId) {
        try {
            await this.orm.call(
                "purchase.price.notification",
                "mark_as_read_or_delete",
                [notifId],
            );
            const idx = this.state.notifications.findIndex((n) => n.id === notifId);
            if (idx !== -1) {
                const wasUnread = this.state.notifications[idx].state === "unread";
                this.state.notifications.splice(idx, 1);
                if (wasUnread) {
                    this.state.count -= 1;
                    priceNotificationCounter.count = this.state.count;
                }
            }
        } catch {
            // silencioso
        }
    }
}

registry.category("systray").add(
    "purchase_invoice_parser.PriceNotificationMenu",
    { Component: PriceNotificationMenu },
    { sequence: 20 },
);
