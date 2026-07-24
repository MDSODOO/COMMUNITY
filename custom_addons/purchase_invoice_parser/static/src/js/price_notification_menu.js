/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

const POLL_INTERVAL_MS = 30_000;

class PriceNotificationMenu extends Component {
    static template = "purchase_invoice_parser.PriceNotificationMenu";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.bus = useService("bus_service");
        this.action = useService("action");

        this.state = useState({
            visible: false,
            open: false,
            count: 0,
            notifications: [],
            loading: false,
        });

        this._boundClose = this._onDocumentClick.bind(this);
        this._pollTimer = null;
        this._busChannel = null;

        // Suscripción síncrona — antes de cualquier await para no perder eventos
        this.bus.subscribe(
            "purchase_invoice_parser/price_update",
            (payload) => this._onBusMessage(payload),
        );

        onMounted(async () => {
            const companyId = user.activeCompany.id;
            this._busChannel = `purchase.price.notification.${companyId}`;
            this.bus.addChannel(this._busChannel);

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
            if (this._busChannel) {
                this.bus.deleteChannel(this._busChannel);
                this._busChannel = null;
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
        } else {
            const idx = this.state.notifications.findIndex((n) => n.id === payload.id);
            if (idx !== -1) {
                Object.assign(this.state.notifications[idx], payload);
                this.state.count = this.state.notifications.filter(
                    (n) => n.state === "unread"
                ).length;
            }
        }
    }

    _onDocumentClick(ev) {
        if (!this.state.open) return;
        const root = this.__owl__.bdom?.el?.closest?.(".pip_price_notification");
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
