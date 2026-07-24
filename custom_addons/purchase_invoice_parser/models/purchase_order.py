from odoo import models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        # Snapshot de precios actuales en supplierinfo ANTES de confirmar,
        # por PO, para detectar divergencias respecto al precio de factura.
        snapshots = {}
        for po in self:
            partner_id = po.partner_id.id
            tmpl_ids = po.order_line.mapped('product_id.product_tmpl_id').ids
            if partner_id and tmpl_ids:
                infos = self.env['product.supplierinfo'].search([
                    ('partner_id', '=', partner_id),
                    ('product_tmpl_id', 'in', tmpl_ids),
                ])
                snapshots[po.id] = {si.product_tmpl_id.id: si.price for si in infos}

        result = super().button_confirm()

        # Generar notificaciones solo para OCs que quedaron confirmadas.
        wizard = self.env['purchase.invoice.import.wizard']
        for po in self.filtered(lambda p: p.state == 'purchase'):
            wizard._notify_price_changes(po, po.company_id, snapshots.get(po.id, {}))

        return result


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def write(self, vals):
        """Notifica cambios MANUALES de precio en líneas de OCs ya confirmadas.

        La creación/confirmación de una OC nueva (manual o vía parser) ya
        queda cubierta por `PurchaseOrder.button_confirm` de arriba (snapshot
        de supplierinfo vs. precio de la línea al confirmar). El gap real es
        editar el precio de una línea DESPUÉS de que la OC ya está confirmada
        (renegociación de costo antes de recibir/facturar) — eso no disparaba
        ninguna notificación. Por eso este override solo actúa sobre líneas
        cuya orden ya está en estado 'purchase'/'done', evitando así generar
        una notificación duplicada para el mismo cambio de precio que
        button_confirm ya habría reportado en el flujo de creación.

        Riesgo de recursión: verificado que HOY no existe — `_notify_price_changes`
        solo hace `Notification.create` (modelo `purchase.price.notification`)
        y `message_post` sobre `product.template`; ninguno de los dos escribe
        `purchase.order.line`, así que no hay ciclo real. Aun así, este write()
        respeta `skip_price_notify` en su propio contexto (línea de abajo) como
        cinturón de seguridad para el futuro, por si algún día `_notify_price_changes`
        necesita escribir algo de vuelta en la línea — bastaría con hacer esa
        escritura vía `line.with_context(skip_price_notify=True).write(...)` para
        que este mismo guard la ignore. La comparación de precio, en cualquier
        caso, se hace SIEMPRE contra el valor real anterior (`line.price_unit`,
        leído antes de `super().write()`), nunca contra el propio `vals` que se
        está por escribir.

        Costeo (FIFO/Promedio): este override solo LEE `price_unit` y crea
        una notificación informativa; no escribe `product.supplierinfo`, ni
        `stock.valuation.layer`, ni ningún campo de costeo. El costo real de
        inventario se calcula a partir de `price_unit` únicamente cuando el
        movimiento de stock se procesa (recepción), no en cada `write()` de
        la línea de compra — por lo que editar el precio de una línea aún no
        recibida es exactamente el flujo ya soportado nativamente por Odoo.
        """
        to_notify = {}
        if 'price_unit' in vals and not self.env.context.get('skip_price_notify'):
            new_price = vals['price_unit']
            for line in self:
                if (
                    line.product_id
                    and line.order_id.state in ('purchase', 'done')
                    and line.price_unit != new_price
                ):
                    tmpl_id = line.product_id.product_tmpl_id.id
                    to_notify.setdefault(line.order_id, {})[tmpl_id] = line.price_unit

        result = super().write(vals)

        if to_notify:
            wizard = self.env['purchase.invoice.import.wizard'].with_context(
                skip_price_notify=True
            )
            for po, old_prices in to_notify.items():
                changed_lines = po.order_line.filtered(
                    lambda l: l.product_id.product_tmpl_id.id in old_prices
                )
                wizard._notify_price_changes(po, po.company_id, old_prices, lines=changed_lines)

        return result
