# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import logging
import re
from datetime import timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)

# Shared regex: strips barcode prefix like "[7501001164164] " from product names.
# Also used in pos_z_report.py — keep both in sync if the pattern ever changes.
_BARCODE_PREFIX_RE = re.compile(r'^\[\d{6,20}\]\s*')


def _clean_product_name(product):
    """Return a product name stripped of its barcode prefix.

    Odoo's default ``display_name`` for products with an internal reference or
    barcode often prepends ``[BARCODE] `` to the name.  This helper removes
    that prefix so the UI can show a cleaner label.

    Args:
        product: A ``product.product`` recordset (single record).

    Returns:
        str: The cleaned product name.
    """
    name = product.display_name or product.name or ''
    barcode = product.barcode
    if barcode:
        name = name.replace(f'[{barcode}] ', '').replace(f'[{barcode}]', '')
    return _BARCODE_PREFIX_RE.sub('', name).strip()


class PosConfig(models.Model):
    _inherit = 'pos.config'

    pos_display_stock = fields.Boolean(string='Mostrar A la mano en POS')
    pos_stock_type = fields.Selection(
        [('onhand', 'A la mano'), ('available', 'A la mano después de reservas')],
        default='onhand',
        string='Tipo de A la mano',
        help='Cifra A la mano que se muestra en la pantalla POS.',
    )
    pos_allow_order = fields.Boolean(
        string='Permitir pedido POS sin A la mano',
    )
    pos_deny_order = fields.Char(
        string='Denegar pedido POS cuando A la mano baje hasta',
    )
    stock_position = fields.Selection(
        [('top_right', 'Top Right'), ('top_left', 'Top Left'), ('bottom_right', 'Bottom Right')],
        default='top_left',
        string='Posición del badge',
    )
    # CHANGED: Removed show_stock_location (frontend-only filter, security flaw).
    # The warehouse/branch is now derived from picking_type_id.default_location_src_id,
    # which is the standard Odoo link between a POS config and its warehouse.
    # This field is kept only as an optional manual override for sub-locations.
    stock_location_id = fields.Many2one(
        'stock.location',
        string='Ubicación de A la mano (override)',
        domain=[('usage', '=', 'internal')],
        help=(
            "Leave empty to automatically use the warehouse linked to this POS "
            "via its Operation Type. Set only to restrict to a specific sub-location "
            "within the warehouse (e.g., a single shelf or zone)."
        ),
    )
    color_background = fields.Char(string='Badge Background Color')
    font_background = fields.Char(string='Badge Font Color')
    low_stock = fields.Float(string='Umbral de alerta A la mano', default=0.00)

    def _get_branch_stock_locations(self):
        """Return all internal stock locations for this POS config's warehouse/branch.

        This is the single source of truth for branch-scoped stock calculations.
        All filtering logic (session load, sync, low-stock report) uses this method.

        Priority:
          1. Manual override: stock_location_id and its internal children.
          2. Standard Odoo path: warehouse root from picking_type_id.default_location_src_id.

        Returns an empty recordset (with a warning) if no location can be resolved,
        so callers can gracefully return empty results instead of crashing.
        """
        self.ensure_one()

        if self.stock_location_id:
            # Manual override configured — use it and all its internal children.
            return self.env['stock.location'].search([
                ('id', 'child_of', self.stock_location_id.id),
                ('usage', '=', 'internal'),
                ('company_id', 'in', [self.company_id.id, False]),
            ])

        # Standard path: the POS Operation Type (picking_type_id) always has a
        # default_location_src_id pointing to the branch's stock location.
        # Use it directly as the root for child_of search to capture all internal
        # sub-locations (e.g. shelves, zones) within that warehouse branch.
        #
        # FIXED: The previous implementation walked UP the hierarchy via a while loop
        # (while parent.usage in 'view'/'internal'), which caused it to reach
        # "Physical Locations" and then collect ALL internal locations across ALL
        # warehouses of the company — completely defeating multi-branch isolation.
        src_location = self.picking_type_id.default_location_src_id
        if not src_location:
            _logger.warning(
                "POS Config '%s' (id=%s) has no source location on its Operation Type '%s'. "
                "Stock will not be filtered by branch. Please configure the Operation Type.",
                self.name, self.id, self.picking_type_id.name or 'N/A',
            )
            return self.env['stock.location']

        # child_of src_location captures src_location itself and any internal sub-zones.
        # This is the correct scope for a single branch/warehouse without crossing into
        # sibling warehouses that share the same "Physical Locations" parent.
        return self.env['stock.location'].search([
            ('id', 'child_of', src_location.id),
            ('usage', '=', 'internal'),
            ('company_id', 'in', [self.company_id.id, False]),
        ])

    def _get_self_ordering_data(self):
        """CHANGED: No longer sends raw stock_location_id or quant_text.
        Branch stock is handled server-side and injected at session load time.
        """
        data = super()._get_self_ordering_data()
        data["config"]["pos_display_stock"] = self.pos_display_stock
        data["config"]["pos_stock_type"] = self.pos_stock_type
        data["config"]["pos_allow_order"] = self.pos_allow_order
        data["config"]["pos_deny_order"] = self.pos_deny_order
        data["config"]["stock_position"] = self.stock_position
        data["config"]["color_background"] = self.color_background
        data["config"]["font_background"] = self.font_background
        data["config"]["low_stock"] = self.low_stock
        return data


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_pos_display_stock = fields.Boolean(
        related="pos_config_id.pos_display_stock", readonly=False,
    )
    pos_pos_stock_type = fields.Selection(
        related="pos_config_id.pos_stock_type", readonly=False,
        string='Tipo de A la mano',
    )
    pos_pos_allow_order = fields.Boolean(
        related="pos_config_id.pos_allow_order", readonly=False,
    )
    pos_pos_deny_order = fields.Char(
        related="pos_config_id.pos_deny_order", readonly=False,
    )
    pos_stock_location_id = fields.Many2one(
        'stock.location',
        related="pos_config_id.stock_location_id",
        domain=[('usage', '=', 'internal')],
        readonly=False,
    )
    pos_stock_position = fields.Selection(
        related="pos_config_id.stock_position", readonly=False,
    )
    pos_color_background = fields.Char(
        related="pos_config_id.color_background", readonly=False,
    )
    pos_font_background = fields.Char(
        related="pos_config_id.font_background", readonly=False,
    )
    pos_low_stock = fields.Float(
        related="pos_config_id.low_stock", readonly=False,
    )


class PosOrder(models.Model):
    _inherit = 'pos.order'

    # Stores the effective stock source location used when the order was placed.
    # Derived from pos.config.stock_location_id or the picking type source.
    location_id = fields.Many2one(
        comodel_name='stock.location',
        related='config_id.stock_location_id',
        string="Ubicación de A la mano (override)",
        store=True,
        readonly=True,
    )

    # Computed stored field for the cashier display name.
    #
    # WHY THIS EXISTS:
    #   In Odoo ≤14 the cashier was stored in a plain Char field called `cashier`.
    #   That field was removed in v15. Odoo 19 uses two fields:
    #     - employee_id (hr.employee) → populated only when "Login con empleados" is ON.
    #     - user_id     (res.users)   → always populated from the session user.
    #   Studio views created in prior versions pointed to the old `cashier` field,
    #   leaving the column empty after migration.
    #   This computed field provides a single, reliable source of truth for both setups.
    cashier_display = fields.Char(
        string='Cajero',
        compute='_compute_cashier_display',
        store=False,
        readonly=True,
    )

    @api.depends('employee_id', 'user_id')
    def _compute_cashier_display(self):
        for order in self:
            order.cashier_display = (
                order.employee_id.name
                or order.user_id.name
                or ''
            )


class StockMoveSyncTrigger(models.Model):
    """Triggers branch-scoped real-time stock sync to POS sessions on confirmed moves.

    FIXED from original (class was mis-named 'stock_quant' but inherited 'stock.move'):
      - Renamed class to be semantically correct.
      - Sync now fires only when state transitions to 'done', not on every write.
        This prevents excessive RPC traffic during multi-step warehouse operations
        (e.g., receipts, internal transfers) that are not yet committed.
      - Sync is deferred to after the DB commit via postcommit hook to eliminate
        the risk of deadlocks during simultaneous branch closings.
    """
    _inherit = 'stock.move'

    def write(self, vals):
        res = super().write(vals)
        # Only trigger sync when a move transitions to 'done'.
        # Any other write (quantity, reference, etc.) does not affect visible POS stock.
        if vals.get('state') == 'done':
            products_to_sync = self.mapped('product_id')
            # Defer to after commit: avoids interfering with the active transaction
            # that created these moves (critical during POS session closing with many pickings).
            self.env.cr.postcommit.add(
                lambda pids=products_to_sync.ids: self._sync_products_after_commit(pids)
            )
        return res

    @api.model
    def _sync_products_after_commit(self, product_ids):
        """Execute branch stock sync in a fresh cursor after the originating transaction commits.

        This decouples the sync from the picking/move transaction, preventing:
          - Deadlocks when 6 branches are closing simultaneously.
          - Partial rollbacks that could send incorrect stock data to POS clients.
        """
        try:
            with self.env.registry.cursor() as new_cr:
                new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                products = new_env['product.product'].browse(product_ids)
                for product in products.exists():
                    product._sync_stock_to_pos()
                new_cr.commit()
        except Exception:
            _logger.exception(
                "Failed to sync stock to POS after commit for product IDs: %s", product_ids
            )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # REMOVED: quant_text field.
    # The original field stored a JSON blob with stock for ALL internal locations
    # across ALL companies. This was a critical cross-branch data leakage vector.
    # Stock quantities are now computed per-session in PosSession._compute_branch_stock()
    # and injected as 'branch_stock' in the session payload.

    @api.model
    def _load_pos_data_fields(self, config_id):
        """CHANGED: Removed quant_text, prod_quant, qty_available, virtual_available.

        Those fields carried global stock data. Branch-scoped stock now arrives
        as the top-level 'branch_stock' key in the session payload, not as per-product fields.
        We still include is_storable and type for the frontend to decide rendering.
        """
        if isinstance(config_id, int):
            config = self.env['pos.config'].browse(config_id)
        else:
            config = config_id
        params = super()._load_pos_data_fields(config)
        # Only safe, non-sensitive fields. No global stock quantities here.
        for field in ['type', 'is_storable', 'product_variant_count']:
            if field not in params:
                params.append(field)
        return params

    @api.model
    def get_low_stock_products(self, low_stock, config_id):
        """Return product IDs whose branch stock is at or below the threshold.

        FIXED: Original method had no branch filter — it returned products
        based on global qty_available, exposing cross-branch inventory data.
        Now scoped to the locations of the requesting POS config.

        Uses read_group for a single aggregated SQL query (no Python loops over quants).
        """
        if not config_id:
            return []

        config = self.env['pos.config'].browse(config_id)
        locations = config._get_branch_stock_locations()
        if not locations:
            return []

        products = self.search([
            ('is_storable', '=', True),
            ('available_in_pos', '=', True),
        ])
        if not products:
            return []

        base_domain = [
            ('product_id', 'in', products.ids),
            ('location_id', 'in', locations.ids),
            ('company_id', '=', config.company_id.id),
        ]

        if config.pos_stock_type == 'available':
            # FIXED: available_quantity is a non-stored computed field in Odoo 19 and
            # cannot be aggregated directly in _read_group (would raise an error or return 0).
            # Same pattern used in _compute_branch_stock(): aggregate quantity and
            # reserved_quantity separately, then compute the difference in Python.
            quant_groups = self.env['stock.quant']._read_group(
                domain=base_domain,
                groupby=['product_id'],
                aggregates=['quantity:sum', 'reserved_quantity:sum'],
            )
            qty_by_product = {
                product.id: max((qty or 0) - (reserved or 0), 0)
                for product, qty, reserved in quant_groups
            }
        else:
            # 'onhand': quantity is a stored field — direct aggregation is safe.
            quant_groups = self.env['stock.quant']._read_group(
                domain=base_domain,
                groupby=['product_id'],
                aggregates=['quantity:sum'],
            )
            qty_by_product = {
                product.id: qty or 0
                for product, qty in quant_groups
            }

        return [pid for pid, qty in qty_by_product.items() if qty <= low_stock]

    @api.model
    def get_top_sold_low_stock(self, low_stock, config_id, days=30):
        """Return low-stock products sorted by POS sales volume (most sold first).

        Combines two dimensions:
          - Branch stock ≤ low_stock threshold (same filter as get_low_stock_products)
          - POS sales quantity in the last `days` days for this branch's POS config

        Sorted: sold_qty DESC, stock_qty ASC (tiebreaker).

        Returns a list of dicts:
            [{'id': int, 'display_name': str, 'stock_qty': float, 'sold_qty': float}, ...]
        """
        if not config_id:
            return []

        config = self.env['pos.config'].browse(config_id)
        locations = config._get_branch_stock_locations()
        if not locations:
            return []

        # ── 1. Low-stock product IDs (branch-scoped) ──────────────────
        low_stock_ids = self.get_low_stock_products(low_stock, config_id)
        if not low_stock_ids:
            return []

        # ── 2. Branch stock qty per product ───────────────────────────
        base_domain = [
            ('product_id', 'in', low_stock_ids),
            ('location_id', 'in', locations.ids),
            ('company_id', '=', config.company_id.id),
        ]
        stock_by_product = {}
        if config.pos_stock_type == 'available':
            quant_groups = self.env['stock.quant']._read_group(
                domain=base_domain,
                groupby=['product_id'],
                aggregates=['quantity:sum', 'reserved_quantity:sum'],
            )
            for product, qty, reserved in quant_groups:
                stock_by_product[product.id] = max((qty or 0) - (reserved or 0), 0)
        else:
            quant_groups = self.env['stock.quant']._read_group(
                domain=base_domain,
                groupby=['product_id'],
                aggregates=['quantity:sum'],
            )
            for product, qty in quant_groups:
                stock_by_product[product.id] = qty or 0

        # ── 3. POS sales qty per product (this config, last N days) ───
        date_from = fields.Datetime.now() - timedelta(days=days)
        sale_groups = self.env['pos.order.line'].sudo()._read_group(
            domain=[
                ('product_id', 'in', low_stock_ids),
                ('order_id.state', 'in', ['done', 'invoiced']),
                ('order_id.config_id', '=', config_id),
                ('order_id.date_order', '>=', date_from),
            ],
            groupby=['product_id'],
            aggregates=['qty:sum'],
        )
        sold_by_product = {
            product.id: max(qty or 0, 0)
            for product, qty in sale_groups
        }

        # ── 4. Build and sort ──────────────────────────────────────────
        products = self.browse(low_stock_ids).exists()
        result = [
            {
                'id': p.id,
                'display_name': _clean_product_name(p),
                'stock_qty': stock_by_product.get(p.id, 0),
                'sold_qty': sold_by_product.get(p.id, 0),
            }
            for p in products
        ]
        # Most sold first; ties broken by lowest stock first
        result.sort(key=lambda r: (-r['sold_qty'], r['stock_qty']))
        return result

    def _sync_stock_to_pos(self):
        """Push branch-scoped stock update to all open POS sessions for this product.

        FIXED: Original sync_product() sent the full quant_text (all branches) to
        ALL POS configs. Now each config receives only its own branch's quantity.
        Also scoped to configs in the same company as the product.
        """
        self.ensure_one()
        pos_configs = self.env['pos.config'].sudo().search([
            ('pos_display_stock', '=', True),
            ('company_id', '=', self.company_id.id),
        ])
        for config in pos_configs:
            locations = config._get_branch_stock_locations()
            if not locations:
                continue
            branch_qty = self._compute_qty_for_locations(locations, config.pos_stock_type)
            # BRANCH_STOCK_UPDATED is consumed by the frontend to update a single product's qty
            config._notify('BRANCH_STOCK_UPDATED', {
                'product_id': self.id,
                'qty': branch_qty,
            })

    def _compute_qty_for_locations(self, locations, stock_type='onhand'):
        """Compute the branch quantity for this product in the given locations.

        Called both from _sync_stock_to_pos (single product) and from
        PosSession._compute_branch_stock (bulk load). Kept on the model
        for reusability without sudo() — caller controls access.

        OPTIMIZED: uses _read_group for a single SQL aggregation instead of
        loading full ORM quant records and summing in Python.
        """
        self.ensure_one()
        domain = [
            ('product_id', '=', self.id),
            ('location_id', 'in', locations.ids),
        ]
        if stock_type == 'available':
            groups = self.env['stock.quant']._read_group(
                domain=domain,
                groupby=[],  # no groupby = single aggregated row
                aggregates=['quantity:sum', 'reserved_quantity:sum'],
            )
            if not groups:
                return 0.0
            qty, reserved = groups[0]
            return max((qty or 0) - (reserved or 0), 0.0)
        else:
            groups = self.env['stock.quant']._read_group(
                domain=domain,
                groupby=[],
                aggregates=['quantity:sum'],
            )
            return float(groups[0][0] or 0.0) if groups else 0.0


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = 'stock.picking'

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        """CHANGED: Added explicit validation for missing source location.

        Original silently fell back to picking_type.default_location_src_id without
        checking if it was set, which could result in stock movements against
        incorrect or unexpected locations in a multi-branch setup.
        """
        pickings = self.env['stock.picking']
        stockable_lines = lines.filtered(
            lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(
                l.qty, precision_rounding=l.product_id.uom_id.rounding
            )
        )
        if not stockable_lines:
            return pickings

        positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
        negative_lines = stockable_lines - positive_lines

        if positive_lines:
            pos_order = positive_lines[0].order_id
            location_id = (
                pos_order.location_id.id
                if pos_order.location_id
                else picking_type.default_location_src_id.id
            )
            if not location_id:
                raise UserError(_(
                    "No se puede validar el pedido POS '%(order)s': no se encontró "
                    "ubicación fuente de A la mano. Configura 'Ubicación de A la mano "
                    "(override)' en el POS o 'Ubicación origen predeterminada' en el "
                    "tipo de operación '%(op_type)s'.",
                    order=pos_order.name,
                    op_type=picking_type.name,
                ))
            vals = self._prepare_picking_vals(partner, picking_type, location_id, location_dest_id)
            positive_picking = self.env['stock.picking'].create(vals)
            positive_picking._create_move_from_pos_order_lines(positive_lines)
            self.env.flush_all()
            try:
                with self.env.cr.savepoint():
                    positive_picking._action_done()
            except (UserError, ValidationError):
                pass
            pickings |= positive_picking

        if negative_lines:
            return_picking_type = picking_type
            return_location_id = picking_type.default_location_src_id.id
            vals = self._prepare_picking_vals(
                partner, return_picking_type, location_dest_id, return_location_id
            )
            negative_picking = self.env['stock.picking'].create(vals)
            negative_picking._create_move_from_pos_order_lines(negative_lines)
            try:
                with self.env.cr.savepoint():
                    negative_picking._action_done()
            except (UserError, ValidationError):
                pass
            pickings |= negative_picking

        return pickings


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        if 'default_location_src_id' not in params:
            params.append('default_location_src_id')
        return params


class StockQuantIndex(models.Model):
    """Helper model solely to create the performance index on stock.quant.

    The index on (location_id, product_id, company_id) is critical for the
    read_group query in _compute_branch_stock() under multi-branch load.
    Without it, PostgreSQL performs a full table scan on stock_quant for
    every POS session open — catastrophic with 6 concurrent branches.
    """
    _inherit = 'stock.quant'

    def _auto_init(self):
        super()._auto_init()
        # Composite index for the branch stock query pattern:
        #   WHERE location_id IN (...) AND product_id IN (...) AND company_id = ?
        # Note: stock_quant has no 'active' column in Odoo 19 — no partial WHERE clause.
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS stock_quant_pos_branch_idx
            ON stock_quant (location_id, product_id, company_id)
        """)
        _logger.info("stock_quant_pos_branch_idx index ensured.")
