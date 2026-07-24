import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    lot_domain = fields.Binary(
        compute="_compute_lot_domain",
        store=False,
    )

    lot_id = fields.Many2one(
        "stock.lot",
        string="Lote",
        domain="lot_domain",
        readonly=False,
    )

    # Campo plano stored — NO compute, NO related.
    # Diseño previo con compute+inverse causaba race condition: al crear
    # un lote inline, lot_id cambia y la recomputación de lot_expiration_date
    # (por dependencia de lot_id.expiration_date) sobreescribía el valor
    # tipeado por el usuario con el default del producto (fecha pasada).
    # Al ser plano, el valor tipeado permanece y write() lo propaga al lote.
    lot_expiration_date = fields.Datetime(
        string="Fecha de Caducidad",
        store=True,
        readonly=False,
    )

    picking_lot_ids = fields.Many2many(
        "stock.lot",
        string="Lotes Recibidos",
        compute="_compute_picking_lots",
        store=False,
    )

    @api.depends("product_id")
    def _compute_lot_domain(self):
        company_id = self.env.company.id
        for line in self:
            product = line.product_id
            if not product or product.tracking not in ("lot", "serial"):
                line.lot_domain = [("id", "=", 0)]
            else:
                line.lot_domain = [
                    ("product_id", "=", product.id),
                    ("company_id", "in", (company_id, False)),
                ]

    @api.onchange("lot_id")
    def _onchange_lot_id_prefill_date(self):
        """UI-only: pre-llena la fecha con la del lote seleccionado SOLO si
        el campo está vacío. Nunca sobreescribe lo que el usuario ya tipeó."""
        for line in self:
            if line.lot_id and not line.lot_expiration_date:
                line.lot_expiration_date = line.lot_id.expiration_date

    @api.onchange("product_id")
    def _onchange_product_clear_lot(self):
        for line in self:
            if line.lot_id and line.lot_id.product_id != line.product_id:
                line.lot_id = False
                line.lot_expiration_date = False

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._sync_lot_expiration_to_stock_lot()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if "lot_expiration_date" in vals or "lot_id" in vals:
            self._sync_lot_expiration_to_stock_lot()
        return res

    def _sync_lot_expiration_to_stock_lot(self):
        """Escribe la fecha de la línea de OC directo en stock.lot.
        Única fuente de verdad. Se invoca en create/write garantizando
        que el lote siempre refleje la fecha ingresada en la OC."""
        for line in self:
            lot = line.lot_id
            fecha = line.lot_expiration_date
            if not lot or not fecha:
                continue
            if lot.expiration_date != fecha:
                _logger.info(
                    "purchase_lot_selection: sync OC→lote '%s' expiration_date "
                    "%s → %s (línea %s)",
                    lot.name, lot.expiration_date, fecha, line.id,
                )
                lot.sudo().expiration_date = fecha

    @api.depends("move_ids.move_line_ids.lot_id")
    def _compute_picking_lots(self):
        if not self:
            return
        real_lines = self.filtered(lambda l: isinstance(l.id, int))
        mapping = {}
        if real_lines:
            mls = self.env["stock.move.line"].search([
                ("move_id.purchase_line_id", "in", real_lines.ids),
                ("lot_id", "!=", False),
            ])
            # Prefetch en una pasada para evitar N+1 en el siguiente loop.
            mls.mapped("move_id.purchase_line_id.id")
            for ml in mls:
                pol_id = ml.move_id.purchase_line_id.id
                if pol_id:
                    mapping.setdefault(pol_id, set()).add(ml.lot_id.id)
        for line in self:
            ids = list(mapping.get(line.id, set()))
            line.picking_lot_ids = [(6, 0, ids)]
