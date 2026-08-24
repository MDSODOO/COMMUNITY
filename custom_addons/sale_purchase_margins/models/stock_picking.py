# -*- coding: utf-8 -*-
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        pickings_to_update = self.filtered(
            lambda picking: (
                picking.state != 'done'
                and picking.picking_type_code == 'incoming'
                and picking.purchase_id
            )
        )

        result = super().button_validate()

        done_pickings = pickings_to_update.filtered(lambda picking: picking.state == 'done')
        if done_pickings:
            done_pickings._qfm_update_supplierinfo_last_cost_from_receipt()

        return result

    def _qfm_update_sale_prices(self):
        """Legacy entry point kept as a no-op.

        Sale price repricing from purchase receipts was disabled intentionally.
        The current receiving automation updates vendor cost on supplierinfo.
        """
        _logger.info(
            'QFM margins: actualización automática de precio de venta '
            'deshabilitada para recepciones.'
        )
        return True

    def _qfm_update_supplierinfo_last_cost_from_receipt(self):
        for picking in self:
            company = picking.company_id or self.env.company
            policy = company.qfm_receipt_price_update_policy or 'always_update'

            for move in picking._qfm_received_purchase_moves():
                purchase_line = move.purchase_line_id

                if policy == 'manual_review':
                    # Solo leer el supplierinfo existente — no crear uno nuevo
                    supplierinfo = picking._qfm_find_supplierinfo(purchase_line)
                    if not supplierinfo:
                        continue
                    last_cost = picking._qfm_purchase_line_cost_for_supplierinfo(
                        purchase_line, supplierinfo,
                    )
                    if last_cost <= 0.0:
                        continue
                    picking._qfm_create_price_notification(
                        supplierinfo, last_cost, purchase_line,
                    )
                    continue

                supplierinfo = picking._qfm_get_or_create_supplierinfo(purchase_line)
                if not supplierinfo:
                    continue

                last_cost = picking._qfm_purchase_line_cost_for_supplierinfo(
                    purchase_line, supplierinfo,
                )
                if last_cost <= 0.0:
                    continue

                # Política only_increase: solo actualizar si el precio subió
                if policy == 'only_increase' and last_cost <= supplierinfo.price:
                    continue

                vals = {'price': last_cost}
                if 'discount' in supplierinfo._fields:
                    vals['discount'] = 0.0
                supplierinfo.sudo().write(vals)

                _logger.info(
                    'QFM margins: costo proveedor actualizado a %.4f '
                    'para %s / %s desde recepción %s',
                    last_cost,
                    purchase_line.product_id.display_name,
                    supplierinfo.partner_id.display_name,
                    picking.name,
                )

    def _qfm_create_price_notification(self, supplierinfo, new_price, purchase_line):
        """Crea una notificación en purchase.price.notification (si el módulo está instalado)
        cuando la política es manual_review y hay un cambio de precio real."""
        Notification = self.env.get('purchase.price.notification')
        if Notification is None:
            return

        old_price = supplierinfo.price
        # Omitir si el precio no cambió o es ruido de redondeo (< 0.1%)
        if not old_price:
            return
        if abs(new_price - old_price) / old_price < 0.001:
            return

        product = purchase_line.product_id
        partner = purchase_line.order_id.partner_id
        company = purchase_line.company_id or self.env.company
        currency = purchase_line.currency_id or company.currency_id

        notif = Notification.create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_name': product.display_name,
            'partner_id': partner.id,
            'partner_name': partner.display_name,
            'old_price': old_price,
            'new_price': new_price,
            'currency_id': currency.id,
            'company_id': company.id,
            'state': 'unread',
        })

        # Enviar evento bus a todos los gestores de inventario activos
        managers = self.env.ref('stock.group_stock_manager').user_ids.filtered(
            lambda u: not u.share
        ).mapped('partner_id')

        currency_symbol = currency.symbol if currency else '$'
        payload = {
            'id': notif.id,
            'product_name': product.display_name,
            'product_tmpl_id': product.product_tmpl_id.id,
            'partner_name': partner.display_name,
            'old_price_fmt': f"{currency_symbol} {old_price:,.2f}",
            'new_price_fmt': f"{currency_symbol} {new_price:,.2f}",
            'purchase_order_name': self.name,
            'state': 'unread',
            'company_id': company.id,
        }
        for manager_partner in managers:
            self.env['bus.bus']._sendone(
                manager_partner,
                'purchase_invoice_parser/price_update',
                payload,
            )

        _logger.info(
            'QFM margins [manual_review]: notificación creada para %s '
            '(%.4f → %.4f) desde recepción %s',
            product.display_name,
            old_price,
            new_price,
            self.name,
        )

    def _qfm_received_purchase_moves(self):
        self.ensure_one()
        return self.move_ids.filtered(
            lambda move: (
                move.state == 'done'
                and move.product_id
                and move.purchase_line_id
                and move.location_dest_id.usage != 'supplier'
                and not move.product_uom.is_zero(move.quantity)
            )
        )

    def _qfm_get_or_create_supplierinfo(self, purchase_line):
        product = purchase_line.product_id
        partner = purchase_line.order_id.partner_id
        company = purchase_line.company_id or self.company_id or self.env.company

        selected_seller = (
            purchase_line.selected_seller_id
            if 'selected_seller_id' in purchase_line._fields
            else False
        )
        if (
            selected_seller
            and selected_seller.product_tmpl_id == product.product_tmpl_id
            and (not selected_seller.product_id or selected_seller.product_id == product)
        ):
            return selected_seller.sudo()

        supplierinfo = self._qfm_find_supplierinfo(purchase_line)
        if supplierinfo:
            return supplierinfo.sudo()

        Supplierinfo = self.env['product.supplierinfo'].sudo()
        vals = {
            'partner_id': partner.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_id': product.id,
            'product_uom_id': (purchase_line.product_uom_id or product.uom_id).id,
            'min_qty': 0.0,
            'price': 0.0,
            'currency_id': (purchase_line.currency_id or company.currency_id).id,
            'company_id': company.id,
        }
        return Supplierinfo.create(vals)

    def _qfm_find_supplierinfo(self, purchase_line):
        product = purchase_line.product_id
        partner = purchase_line.order_id.partner_id
        company = purchase_line.company_id or self.company_id or self.env.company
        receipt_date = fields.Date.to_date(
            self.date_done
            or purchase_line.order_id.date_approve
            or purchase_line.order_id.date_order
        ) or fields.Date.context_today(self)

        sellers = self.env['product.supplierinfo'].sudo().search([
            ('partner_id', '=', partner.id),
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', company.id),
            '|',
            ('product_id', '=', product.id),
            ('product_id', '=', False),
        ])
        dated_sellers = sellers.filtered(
            lambda seller: (
                (not seller.date_start or seller.date_start <= receipt_date)
                and (not seller.date_end or seller.date_end >= receipt_date)
            )
        )
        sellers = dated_sellers or sellers
        if not sellers:
            return self.env['product.supplierinfo']

        return sellers.sorted(
            key=lambda seller: (
                0 if seller.product_id == product else 1,
                0 if seller.company_id == company else 1,
                0 if seller.product_uom_id == purchase_line.product_uom_id else 1,
                seller.sequence,
                -(seller.min_qty or 0.0),
                seller.id,
            )
        )[:1]

    def _qfm_purchase_line_cost_for_supplierinfo(self, purchase_line, supplierinfo):
        product = purchase_line.product_id
        company = purchase_line.company_id or self.company_id or self.env.company
        source_currency = purchase_line.currency_id or company.currency_id
        target_currency = supplierinfo.currency_id or source_currency
        source_uom = purchase_line.product_uom_id or product.uom_id
        target_uom = supplierinfo.product_uom_id or product.uom_id

        cost = purchase_line.price_unit or 0.0
        if 'price_unit_discounted' in purchase_line._fields:
            cost = purchase_line.price_unit_discounted or 0.0
        elif 'discount' in purchase_line._fields and purchase_line.discount:
            cost *= 1.0 - (purchase_line.discount / 100.0)

        if source_uom != target_uom:
            cost = source_uom._compute_price(cost, target_uom)

        cost_date = fields.Date.to_date(
            self.date_done
            or purchase_line.order_id.date_approve
            or purchase_line.order_id.date_order
        ) or fields.Date.context_today(self)
        if source_currency != target_currency:
            cost = source_currency._convert(
                cost,
                target_currency,
                company,
                cost_date,
            )

        return target_currency.round(cost)
