import logging
from odoo import models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = 'stock.picking'

    def _action_assign(self, force_qty=False):
        res = super()._action_assign(force_qty=force_qty)
        self._propagar_lotes_de_compra()
        return res

    def button_validate(self):
        # Última sincronización OC→lote antes del chequeo de caducados
        # que dispara Odoo en la validación del picking.
        self._sync_expiration_dates_from_po()
        return super().button_validate()

    def _sync_expiration_dates_from_po(self):
        for picking in self:
            for move in picking.move_ids:
                pol = move.purchase_line_id
                if not pol or not pol.lot_id:
                    continue
                lot = pol.lot_id
                fecha = pol.lot_expiration_date
                if fecha and lot.expiration_date != fecha:
                    _logger.info(
                        "purchase_lot_selection: re-sync en button_validate "
                        "lote '%s' %s → %s (picking %s)",
                        lot.name, lot.expiration_date, fecha, picking.name,
                    )
                    lot.sudo().expiration_date = fecha

    def _propagar_lotes_de_compra(self):
        """
        Para cada movimiento con lote preseleccionado en la OC:
          - Sincroniza la fecha de caducidad del lote con la de la OC.
          - Si ya existen move_line_ids sin lote → asigna el lote.
          - Si no existen y hay cantidad > 0 → crea move_line_ids en batch.

        Respeta:
          - Serial + qty > 1 (omite; requiere serie única por unidad).
          - Unicidad de serie (no re-usa seriales ya recibidos).
          - Multi-compañía (solo propaga lotes de la misma compañía).
          - Estrategia de putaway en la ubicación destino.
        """
        SML = self.env['stock.move.line']

        self.mapped('move_ids.purchase_line_id.lot_id')
        self.mapped('move_ids.move_line_ids.lot_id')

        vals_list = []
        write_buckets = {}

        for picking in self:
            for move in picking.move_ids:
                if move.state in ('cancel', 'done'):
                    continue
                if move.product_id.tracking == 'none':
                    continue

                pol = move.purchase_line_id
                if not pol or not pol.lot_id:
                    continue

                lot = pol.lot_id

                if lot.product_id != move.product_id:
                    _logger.warning(
                        "purchase_lot_selection: lote '%s' (producto '%s') no coincide "
                        "con movimiento %s (producto '%s'). Se omite.",
                        lot.name, lot.product_id.display_name,
                        move.id, move.product_id.display_name,
                    )
                    continue

                if lot.company_id and lot.company_id != picking.company_id:
                    _logger.warning(
                        "purchase_lot_selection: lote '%s' compañía %s != picking %s "
                        "compañía %s. Se omite.",
                        lot.name, lot.company_id.name,
                        picking.id, picking.company_id.name,
                    )
                    continue

                fecha = pol.lot_expiration_date
                if fecha and lot.expiration_date != fecha:
                    _logger.info(
                        "purchase_lot_selection: sync (_propagar) lote '%s' %s → %s",
                        lot.name, lot.expiration_date, fecha,
                    )
                    lot.sudo().expiration_date = fecha

                tracking = move.product_id.tracking

                try:
                    if move.move_line_ids:
                        sin_lote = move.move_line_ids.filtered(lambda ml: not ml.lot_id)
                        if sin_lote:
                            write_buckets.setdefault(lot.id, []).extend(sin_lote.ids)
                        continue

                    qty = move.product_uom_qty
                    if not qty or qty <= 0:
                        continue

                    if tracking == 'serial' and qty > 1:
                        _logger.info(
                            "purchase_lot_selection: producto serial '%s' con qty=%s > 1; "
                            "se omite auto-propagación (una serie por unidad requerida).",
                            move.product_id.display_name, qty,
                        )
                        continue

                    if tracking == 'serial':
                        ya_usado = SML.search_count([
                            ('lot_id', '=', lot.id),
                            ('state', '=', 'done'),
                        ])
                        if ya_usado:
                            _logger.warning(
                                "purchase_lot_selection: serie '%s' ya usada en "
                                "recepción previa. Se omite.",
                                lot.name,
                            )
                            continue

                    location_dest = move.location_dest_id
                    try:
                        putaway = location_dest._get_putaway_strategy(
                            move.product_id,
                            quantity=qty,
                        )
                        if putaway:
                            location_dest = putaway
                    except Exception as exc:
                        _logger.warning(
                            "purchase_lot_selection: putaway falló para move %s: %s",
                            move.id, exc, exc_info=True,
                        )

                    vals_list.append({
                        'move_id': move.id,
                        'picking_id': picking.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_uom.id,
                        'location_id': move.location_id.id,
                        'location_dest_id': location_dest.id,
                        'lot_id': lot.id,
                        'quantity': qty,
                        'company_id': picking.company_id.id,
                    })

                except (UserError, ValidationError) as e:
                    _logger.warning(
                        "purchase_lot_selection: lote '%s' no propagado a move %s "
                        "(picking %s): %s",
                        lot.name, move.id, picking.id, e,
                    )

        for lot_id, ml_ids in write_buckets.items():
            SML.browse(ml_ids).write({'lot_id': lot_id})

        if vals_list:
            SML.create(vals_list)
