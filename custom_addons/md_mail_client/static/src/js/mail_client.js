/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onMounted, onWillDestroy, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

const FOLDERS = [
    { key: "all", label: "Todo", domain: [], icon: "fa-inbox" },
    // "inbox"/"sent" ya no llevan filtro de 'state' fijo: el filtro real por
    // destinatario/autor se arma dinamicamente en currentDomain() porque
    // depende del usuario conectado (user.partnerId).
    { key: "inbox", label: "Recibidos", domain: [], icon: "fa-inbox" },
    { key: "starred", label: "Destacados", domain: [["starred", "=", true]], icon: "fa-star-o" },
    { key: "sent", label: "Enviados", domain: [], icon: "fa-paper-plane-o" },
    { key: "draft", label: "Borradores / En cola", domain: [["state", "in", ["outgoing", "exception"]]], icon: "fa-pencil" },
    { key: "trash", label: "Papelera", domain: [["state", "=", "cancel"]], icon: "fa-trash-o" },
];

const BRANCH_COLORS = ["#7a9cc6", "#c68b5a", "#8ab07a", "#c65a7a", "#5ac6b8", "#b09a5a"];
const AVATAR_PALETTE = [
    "#714b67", "#4f7cac", "#c9784f", "#5a9d6b", "#a85a8a", "#b58a3c", "#5a8bb0", "#8a5ac9",
];

const MESSAGE_FIELDS = [
    "id", "subject", "email_from", "email_to", "date", "state", "starred", "author_id",
    "record_company_id", "partner_ids", "recipient_ids",
];
const FULL_FIELDS = [...MESSAGE_FIELDS, "body_html"];

function hashColor(name) {
    let h = 0;
    for (let i = 0; i < (name || "").length; i++) {
        h = (h * 31 + name.charCodeAt(i)) % AVATAR_PALETTE.length;
    }
    return AVATAR_PALETTE[Math.abs(h)];
}

export class MdMailClient extends Component {
    static template = "md_mail_client.MailClient";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.busService = useService("bus_service");
        this.folders = FOLDERS;
        this.state = useState({
            folderKey: "all",
            branchId: null,
            messages: [],
            selectedId: null,
            selected: null,
            loading: true,
            query: "",
            branches: [],
            unreadCount: 0, // NUEVO: badge para "Recibidos" (bus en tiempo real)
        });
        onWillStart(async () => {
            await this.loadBranches();
            await this.loadFolder("all");
            await this._refreshUnreadCount();
        });
        onMounted(() => this._setupRealtimeSync());
        onWillDestroy(() => this._teardownRealtimeSync());
    }

    async loadBranches() {
        const companies = await this.orm.searchRead("res.company", [], ["id", "name"], { order: "name" });
        this.state.branches = companies.map((c, i) => ({
            id: c.id,
            name: c.name.replace(/^MDS\s*/i, ""),
            color: BRANCH_COLORS[i % BRANCH_COLORS.length],
        }));
    }

    folderLabel(key) {
        const f = this.folders.find((x) => x.key === key);
        return f ? f.label : "";
    }

    // --- PROBLEMA 2: dominios de "Recibidos"/"Enviados" ---------------------
    // PROBLEM 2: "Inbox"/"Sent" domains.
    //
    // mail.mail hereda por delegacion (_inherits) de mail.message, por lo que
    // 'author_id' y 'partner_ids' viven realmente en mail.message aunque se
    // consulten desde mail.mail. 'recipient_ids' SI es propio de mail.mail
    // ("To (Partners)" de ese envio puntual).
    //
    // Antes: "Recibidos" filtraba por state == 'received', un estado que
    // mail.mail casi nunca setea (solo aplica a integracion fetchmail/IMAP,
    // que este modulo no tiene instalada) -> el buzon quedaba SIEMPRE vacio.
    // "Enviados" filtraba solo por state == 'sent', sin acotar por autor, por
    // lo que mostraba TODO correo saliente del sistema, de cualquier usuario.
    //
    // Ahora: se filtra por destinatario/autor real (res.partner del usuario
    // conectado), que es la unica nocion de "recibido"/"enviado" disponible
    // sin una integracion IMAP real.
    currentDomain() {
        const folder = this.folders.find((f) => f.key === this.state.folderKey);
        let domain = folder.domain;
        const partnerId = user.partnerId;

        if (folder.key === "sent") {
            domain = domain.concat([["author_id", "=", partnerId]]);
        } else if (folder.key === "inbox") {
            domain = domain.concat([
                ["recipient_ids", "in", [partnerId]],
                ["author_id", "!=", partnerId],
            ]);
        }

        if (this.state.branchId) {
            domain = domain.concat([["record_company_id", "=", this.state.branchId]]);
        }
        if (this.state.query) {
            domain = domain.concat([["subject", "ilike", this.state.query]]);
        }
        return domain;
    }

    async loadFolder(key) {
        this.state.folderKey = key;
        await this.reload();
        if (key === "inbox") {
            this.state.unreadCount = 0; // se "leyo" el buzon
        }
    }

    async filterBranch(id) {
        this.state.branchId = this.state.branchId === id ? null : id;
        await this.reload();
    }

    async reload() {
        this.state.loading = true;
        const records = await this.orm.searchRead("mail.mail", this.currentDomain(), MESSAGE_FIELDS, {
            order: "date desc",
            limit: 100,
        });
        this.state.messages = records;
        this.state.loading = false;
        if (records.length) {
            await this.select(records[0].id);
        } else {
            this.state.selectedId = null;
            this.state.selected = null;
        }
    }

    async onSearch(ev) {
        this.state.query = ev.target.value;
        await this.reload();
    }

    senderName(msg) {
        if (msg.author_id) {
            return msg.author_id[1];
        }
        if (msg.email_from) {
            return msg.email_from.split("<")[0].trim() || msg.email_from;
        }
        return "Sistema";
    }

    initials(name) {
        const parts = (name || "?").trim().split(/\s+/);
        const letters = parts.slice(0, 2).map((p) => p[0] || "").join("");
        return letters.toUpperCase() || "?";
    }

    avatarColor(name) {
        return hashColor(name || "?");
    }

    stateLabel(state) {
        return {
            outgoing: "En cola",
            sent: "Enviado",
            received: "Recibido",
            exception: "Sin enviar",
            cancel: "Cancelado",
        }[state] || state;
    }

    async select(id) {
        this.state.selectedId = id;
        const [full] = await this.orm.read("mail.mail", [id], FULL_FIELDS);
        full.body_html = markup(full.body_html || "<p><em>Sin contenido.</em></p>");
        this.state.selected = full;
    }

    async toggleStar(ev, id) {
        ev.stopPropagation();
        const msg = this.state.messages.find((m) => m.id === id);
        const newVal = !msg.starred;
        await this.orm.write("mail.mail", [id], { starred: newVal });
        msg.starred = newVal;
        if (this.state.selected && this.state.selected.id === id) {
            this.state.selected.starred = newVal;
        }
    }

    // --- PROBLEMA 1: "Redactar" independiente --------------------------------
    // PROBLEM 1: standalone "Compose".
    //
    // mail.compose.message en modo 'comment' revienta con "should run on at
    // least one record" SOLO si 'res_ids' queda vacio (ver
    // odoo/addons/mail/wizard/mail_compose_message.py:780-810,
    // _action_send_mail). Si 'model' NO se define, el wizard usa como
    // fallback 'mail.thread' generico y llama a message_notify() SIN atar el
    // correo a ningun registro real de negocio -- exactamente lo que
    // necesitamos para un correo suelto.
    //
    // Por eso: NO seteamos 'default_model'. Solo garantizamos que
    // 'default_res_ids' sea una lista no vacia (su contenido es irrelevante
    // porque, al no haber 'model', nunca se hace browse() contra un registro
    // real). Esto reemplaza el hack anterior de anclar el compositor al
    // res.partner del remitente/usuario, que como efecto secundario dejaba
    // el correo registrado en el chatter de ese contacto.
    _composeContext(extra = {}) {
        return {
            default_composition_mode: "comment",
            default_res_ids: JSON.stringify([user.partnerId]),
            ...extra,
        };
    }

    async _openComposer(extra) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "mail.compose.message",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: this._composeContext(extra),
        });
    }

    async compose() {
        await this._openComposer({});
    }

    async reply() {
        const m = this.state.selected;
        if (!m) return;
        await this._openComposer({
            default_subject: (m.subject || "").startsWith("Re: ") ? m.subject : `Re: ${m.subject || ""}`,
            default_partner_ids: m.author_id ? [m.author_id[0]] : [],
        });
    }

    async forward() {
        const m = this.state.selected;
        if (!m) return;
        await this._openComposer({
            default_subject: (m.subject || "").startsWith("Fwd: ") ? m.subject : `Fwd: ${m.subject || ""}`,
            default_body: m.body_html || "",
        });
    }

    // --- PROBLEMA 3: sincronizacion en tiempo real via bus -------------------
    // PROBLEM 3: real-time sync via bus_service.
    //
    // El websocket de Odoo ya suscribe automaticamente cada sesion logueada
    // al canal de su propio res.partner (ir/websocket ->
    // _build_bus_channel_list: "if req.session.uid: channels.append(
    // self.env.user.partner_id)"). No hace falta addChannel manual para nuestro
    // propio buzon (a diferencia de canales de discuss.channel, que si lo
    // requieren).
    //
    // El evento que Odoo 19 emite para altas de mail.message es
    // "mail.record/insert" (unificado; en 17/18 era "mail.message/insert").
    // El payload trae forma de "Store" interno de Discuss
    // (p.ej. payload["mail.message"] = [...]), cuya forma exacta puede variar
    // entre versiones/parches. Para no acoplarnos a ese detalle interno,
    // usamos el evento solo como SEÑAL para: (a) refrescar un contador de no
    // leidos via ORM (fuente de verdad propia, con nuestro dominio de
    // "Recibidos"), y (b) recargar la lista si el folder activo es
    // "Recibidos"/"Todo". Con debounce para no golpear el ORM en rafagas.
    _setupRealtimeSync() {
        this._syncTimer = null;
        this._onBusInsert = (payload) => {
            if (!payload || !payload["mail.message"]) {
                return;
            }
            this._scheduleSync();
        };
        this._onBusReconnect = () => this._scheduleSync();

        this.busService.subscribe("mail.record/insert", this._onBusInsert);
        this.busService.addEventListener("BUS:CONNECT", this._onBusReconnect);
    }

    _teardownRealtimeSync() {
        this.busService.unsubscribe("mail.record/insert", this._onBusInsert);
        this.busService.removeEventListener("BUS:CONNECT", this._onBusReconnect);
        clearTimeout(this._syncTimer);
    }

    _scheduleSync() {
        clearTimeout(this._syncTimer);
        this._syncTimer = setTimeout(() => this._refreshUnreadCount(), 400);
    }

    async _refreshUnreadCount() {
        const count = await this.orm.searchCount("mail.mail", [
            ["recipient_ids", "in", [user.partnerId]],
            ["author_id", "!=", user.partnerId],
        ]);
        this.state.unreadCount = count;
        if (this.state.folderKey === "inbox" || this.state.folderKey === "all") {
            await this.reload();
        }
    }
}

registry.category("actions").add("md_mail_client.client_action", MdMailClient);
