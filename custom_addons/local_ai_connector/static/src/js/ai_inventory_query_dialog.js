/** @odoo-module **/
/**
 * Dialogo del copiloto de inventario: el staff escribe una pregunta en
 * lenguaje natural, se manda a /ai/inventory_query (auth='user', backend
 * de local_ai_connector), y se muestra la respuesta tal cual la devolvio
 * Odoo -- el numero "A la mano" siempre viene calculado por Python contra
 * stock.quant real, nunca redactado por el modelo (ver
 * services/inventory_nl_resolver.py).
 */

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";

export class AiInventoryQueryDialog extends Component {
    static template = "local_ai_connector.AiInventoryQueryDialog";
    static components = { Dialog };
    static props = { close: Function };

    setup() {
        this.state = useState({
            question: "",
            loading: false,
            result: null, // { status, message }
        });
    }

    async ask() {
        const question = this.state.question.trim();
        if (!question) {
            return;
        }
        this.state.loading = true;
        this.state.result = null;
        try {
            const result = await rpc("/ai/inventory_query", { question });
            this.state.result = result;
        } catch (err) {
            this.state.result = {
                status: "error",
                message: "No se pudo contactar al copiloto de inventario. Intenta de nuevo.",
            };
        } finally {
            this.state.loading = false;
        }
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.ask();
        }
    }

    get resultClass() {
        const cls = {
            ok: "alert-success",
            clarify: "alert-warning",
            not_found: "alert-warning",
            error: "alert-danger",
        };
        return this.state.result ? (cls[this.state.result.status] || "alert-secondary") : "";
    }
}
