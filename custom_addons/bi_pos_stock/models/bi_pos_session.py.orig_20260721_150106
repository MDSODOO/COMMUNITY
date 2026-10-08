# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import base64
import io
import logging
from dateutil.relativedelta import relativedelta
from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.addons.bi_pos_stock.models.bi_pos_stock import _clean_product_name

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    _X_LINE_MODEL = 'x_line'
    _X_LINE_CANDIDATE_FIELDS = (
        'name',
        'x_name',
        'x_studio_name',
        'x_studio_sequence',
        'sequence',
        'active',
        'create_date',
        'write_date',
    )

    def _load_pos_data_models(self, config_id):
        """Keep stock.location in the loaded models list for location name display."""
        res = super()._load_pos_data_models(config_id)
        if 'stock.location' not in res:
            res.append('stock.location')
        x_line = self._X_LINE_MODEL
        if (
            x_line in self.env.registry.models
            and hasattr(self.env[x_line], '_load_pos_data_fields')
            and x_line not in res
        ):
            res.append(x_line)
        return res

    def _load_pos_data(self, *args, **kwargs):
        """Inject Studio model data into the POS bootstrap payload when present."""
        data = super()._load_pos_data(*args, **kwargs)
        data[self._X_LINE_MODEL] = self.get_x_line_data()
        return data

    def _get_x_line_fields(self):
        """Return the safe subset of Studio x_line fields available in this DB."""
        if self._X_LINE_MODEL not in self.env.registry.models:
            return []
        available_fields = self.env[self._X_LINE_MODEL].fields_get().keys()
        return [
            field_name
            for field_name in self._X_LINE_CANDIDATE_FIELDS
            if field_name in available_fields
        ]

    def get_x_line_data(self):
        """Return Studio model x_line records for the POS frontend.

        Studio models can differ between databases. This method reads only
        fields that exist in the active registry and gracefully returns an
        empty list when x_line is not installed, so POS startup is never blocked.
        """
        if self._X_LINE_MODEL not in self.env.registry.models:
            return []

        XLine = self.env[self._X_LINE_MODEL].sudo()
        fields_to_read = self._get_x_line_fields() or ['id']
        domain = [('active', '=', True)] if 'active' in fields_to_read else []
        return XLine.search_read(
            domain=domain,
            fields=fields_to_read,
            order='id asc',
        )

    def _get_product_x_line_value(self, product):
        """Return (line_id, line_name) for a product's Studio x_line relation."""
        candidate_field_names = (
            'x_line_id',
            'x_line',
            'x_studio_line_id',
            'x_studio_line',
            'x_studio_linea_id',
            'x_studio_linea',
            'x_studio_lnea_id',
            'x_studio_lnea',
        )

        def read_line_value(record):
            for field_name in candidate_field_names:
                if field_name in record._fields:
                    value = record[field_name]
                    if value:
                        return value

            for field_name, field in record._fields.items():
                if getattr(field, 'comodel_name', None) == self._X_LINE_MODEL:
                    value = record[field_name]
                    if value:
                        return value
            return False

        value = read_line_value(product) or read_line_value(product.product_tmpl_id)
        if not value:
            return False, ''

        if hasattr(value, 'ids'):
            return value.id, value.display_name or value.name or ''
        return False, str(value)

    def get_branch_stock(self):
        """Return branch-scoped stock quantities for this POS session.

        Called from the POS frontend via RPC in processServerData() (Odoo 19+).
        In Odoo 19, processServerData() takes no arguments and data is no longer
        passed via _load_pos_data(). Custom data must be fetched via a direct
        RPC call from the frontend.

        This is the SECURITY BOUNDARY of the entire module.

        Returns:
            {
                'branch_stock': {str(product_id): float(qty)},  # branch-scoped quantities
                'branch_stock_config': {...}                     # display/validation params
            }
        """
        self.ensure_one()
        config = self.config_id

        if not config.pos_display_stock:
            return {'branch_stock': {}, 'branch_stock_config': {}}

        return {
            'branch_stock': self._compute_branch_stock(),
            'branch_stock_config': {
                'stock_type': config.pos_stock_type,
                'allow_order': config.pos_allow_order,
                'deny_order': config.pos_deny_order or 0,
                'low_stock': config.low_stock,
                'stock_position': config.stock_position,
                'color_background': config.color_background or '#4caf50',
                'font_background': config.font_background or '#ffffff',
            },
        }

    def _compute_branch_stock(self):
        """Compute per-product stock quantities scoped to this POS's branch locations.

        PERFORMANCE DESIGN:
          - Single SQL query via read_group (no Python-level quant iteration).
          - Query is bounded by: location_id IN (...), company_id = ?, product_id IN (...)
          - The stock_quant_pos_branch_idx index (created in bi_pos_stock.py) makes
            this query O(log n) even with large quant tables.
          - Returns only products that have actual quant records (sparse dict).
            Products with no quants default to 0 on the frontend.

        MULTI-BRANCH SAFETY:
          - _get_branch_stock_locations() returns only locations for THIS warehouse.
          - company_id filter prevents cross-company data leakage.
        """
        config = self.config_id
        locations = config._get_branch_stock_locations()

        if not locations:
            _logger.warning(
                "POS Session '%s': _compute_branch_stock found no locations for config '%s'. "
                "Check the Operation Type or Override Stock Location configuration.",
                self.name, config.name,
            )
            return {}

        products = self.env['product.product'].search([
            ('available_in_pos', '=', True),
            ('is_storable', '=', True),
        ])
        if not products:
            return {}

        base_domain = [
            ('product_id', 'in', products.ids),
            ('location_id', 'in', locations.ids),
            ('company_id', '=', config.company_id.id),
        ]

        if config.pos_stock_type == 'available':
            # available_quantity is a non-stored computed field in Odoo 19 and cannot
            # be aggregated directly. Compute it as on-hand minus reserved.
            on_hand_groups = self.env['stock.quant']._read_group(
                domain=base_domain,
                groupby=['product_id'],
                aggregates=['quantity:sum', 'reserved_quantity:sum'],
            )
            return {
                str(product.id): max((quantity or 0) - (reserved or 0), 0)
                for product, quantity, reserved in on_hand_groups
            }
        else:
            # 'onhand': quantity is a stored field — direct aggregation is safe.
            on_hand_groups = self.env['stock.quant']._read_group(
                domain=base_domain,
                groupby=['product_id'],
                aggregates=['quantity:sum'],
            )
            return {
                str(product.id): quantity or 0
                for product, quantity in on_hand_groups
            }


    def get_pos_stock_data(self):
        """Single RPC entry point for all stock data needed at POS session open.

        Replaces the three sequential RPC calls that were previously made from
        processServerData() in models.js:
          - get_branch_stock()
          - get_lots_expiry_summary()
          - get_all_lot_details()

        Consolidating them eliminates 2 extra network round-trips (~400-800ms)
        on every POS session open, especially noticeable on slow LAN connections.

        Returns:
            {
                'branch_stock':        {str(product_id): float},
                'branch_stock_config': {stock_type, allow_order, ...},
                'lots_expiry_summary': {str(tmpl_id): {lot_name, expiration_date, qty}},
                'all_lot_details':     {"pid_lotname": {product_id, expiration_date, qty}},
            }
        """
        self.ensure_one()

        # Branch stock (already optimized with read_group in _compute_branch_stock)
        stock_result = self.get_branch_stock()

        # Lot expiry data — both methods are now optimized with search_read + batch load
        lots_expiry = self.get_lots_expiry_summary()
        all_lot_details = self.get_all_lot_details()

        return {
            **stock_result,
            'lots_expiry_summary': lots_expiry,
            'all_lot_details': all_lot_details,
        }

    def get_replenishment_data(self):
        """Return orderpoint products where branch on-hand qty <= product_min_qty.

        Called from the POS frontend via RPC (navbar show_products button).
        Scoped to the branch locations of this session's POS config — never
        crosses to other branches.

        Returns a list of dicts:
            [{
                'orderpoint_id': int,
                'product_id': int,
                'display_name': str,
                'barcode': str,
                'qty_on_hand': float,
                'product_min_qty': float,
                'product_max_qty': float,
                'qty_to_order': float,
                'location_name': str,
            }, ...]

        Sorted by urgency: most below minimum first (qty_on_hand - product_min_qty ASC).
        """
        self.ensure_one()
        config = self.config_id
        locations = config._get_branch_stock_locations()
        if not locations:
            return []

        orderpoints = self.env['stock.warehouse.orderpoint'].search([
            ('location_id', 'in', locations.ids),
            ('active', '=', True),
        ])
        if not orderpoints:
            return []

        # OPTIMIZED: batch _read_group instead of per-orderpoint _compute_qty_for_locations().
        # Single SQL query for all orderpoint products at once.
        product_ids = orderpoints.mapped('product_id').ids
        base_domain = [
            ('product_id', 'in', product_ids),
            ('location_id', 'in', locations.ids),
            ('company_id', '=', config.company_id.id),
        ]

        if config.pos_stock_type == 'available':
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
            quant_groups = self.env['stock.quant']._read_group(
                domain=base_domain,
                groupby=['product_id'],
                aggregates=['quantity:sum'],
            )
            qty_by_product = {
                product.id: qty or 0
                for product, qty in quant_groups
            }

        result = []
        for op in orderpoints:
            qty_on_hand = qty_by_product.get(op.product_id.id, 0.0)
            if qty_on_hand <= op.product_min_qty:
                qty_to_order = max(op.product_max_qty - qty_on_hand, 0)
                result.append({
                    'orderpoint_id': op.id,
                    'product_id': op.product_id.id,
                    'display_name': _clean_product_name(op.product_id),
                    'barcode': op.product_id.barcode or '',
                    'qty_on_hand': qty_on_hand,
                    'product_min_qty': op.product_min_qty,
                    'product_max_qty': op.product_max_qty,
                    'qty_to_order': qty_to_order,
                    'location_name': op.location_id.complete_name,
                })

        # Most urgent first: largest deficit below minimum
        result.sort(key=lambda r: r['qty_on_hand'] - r['product_min_qty'])
        return result

    def create_replenishment_transfer(self, orderpoint_id):
        """Create an internal transfer from the warehouse's main stock to the branch location.

        Called from the POS frontend when the cashier clicks "Solicitar Reabastecimiento"
        on a specific product row.

        Flow:
          Source location  → warehouse.lot_stock_id  (main stock)
          Dest location    → orderpoint.location_id  (POS branch shelf/location)
          Qty              → product_max_qty - branch_on_hand  (fill to max)

        Returns:
            {'success': True,  'picking_name': str, 'qty_to_order': float, 'product_name': str}
            {'success': False, 'message': str}
        """
        self.ensure_one()
        config = self.config_id
        orderpoint = self.env['stock.warehouse.orderpoint'].browse(orderpoint_id)

        if not orderpoint.exists():
            return {'success': False, 'message': _('Regla de reabastecimiento no encontrada.')}

        # Re-compute branch qty at request time to get the most up-to-date value
        locations = config._get_branch_stock_locations()
        qty_on_hand = orderpoint.product_id._compute_qty_for_locations(
            locations, config.pos_stock_type
        )
        qty_to_order = max(orderpoint.product_max_qty - qty_on_hand, 0)

        if qty_to_order <= 0:
            return {
                'success': False,
                'message': _(
                    'El producto "%(name)s" ya tiene A la mano suficiente '
                    '(%(qty).0f unidades A la mano).',
                    name=orderpoint.product_id.display_name,
                    qty=qty_on_hand,
                ),
            }

        # sudo() is required: in multi-company setups an ir.rule on stock.warehouse
        # scopes records by the user's active company, which may differ from the
        # session's company. The warehouse here is resolved from the POS config's
        # own picking type — not user-supplied input — so sudo is architecturally safe.
        warehouse = config.sudo().picking_type_id.warehouse_id
        if not warehouse:
            return {'success': False, 'message': _('No se encontró almacén para esta caja POS.')}

        source_location = warehouse.lot_stock_id
        dest_location = orderpoint.location_id

        if source_location == dest_location:
            return {
                'success': False,
                'message': _(
                    'La ubicación de origen y destino son la misma (%s). '
                    'Verifica la configuración del orderpoint.',
                    source_location.complete_name,
                ),
            }

        # Internal picking type for this warehouse
        internal_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', warehouse.id),
            ('code', '=', 'internal'),
        ], limit=1)

        if not internal_type:
            return {
                'success': False,
                'message': _(
                    'No se encontró tipo de operación interna para el almacén "%s".',
                    warehouse.name,
                ),
            }

        product = orderpoint.product_id
        picking = self.env['stock.picking'].sudo().create({
            'picking_type_id': internal_type.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'origin': _('POS Reabastecimiento - %(pos)s', pos=config.name),
            'move_ids': [(0, 0, {
                'name': product.display_name,
                'product_id': product.id,
                'product_uom_qty': qty_to_order,
                'product_uom': product.uom_id.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
            })],
        })

        _logger.info(
            "POS '%s': replenishment transfer %s created for product '%s' "
            "(qty=%.2f, %s → %s).",
            config.name, picking.name, product.display_name,
            qty_to_order, source_location.complete_name, dest_location.complete_name,
        )

        return {
            'success': True,
            'picking_id': picking.id,
            'picking_name': picking.name,
            'qty_to_order': qty_to_order,
            'product_name': product.display_name,
        }


    # -------------------------------------------------------------------------
    # Feature: General Replenishment Screen (Ventas Trimestrales)
    # -------------------------------------------------------------------------

    def _get_branch_pos_config_ids(self):
        """Return POS configs that share this session's physical stock source.

        Inventory quantities are already scoped by stock.location. Historical
        sales must follow the same branch boundary so two cash registers in the
        same store see identical "Inventario General" numbers instead of each
        register seeing only its own POS orders.
        """
        self.ensure_one()
        config = self.config_id
        branch_root = config.stock_location_id or config.picking_type_id.default_location_src_id
        if not branch_root:
            return [config.id]

        branch_config_ids = []
        candidate_configs = self.env['pos.config'].sudo().search([
            ('company_id', '=', config.company_id.id),
        ])
        for candidate in candidate_configs:
            candidate_root = (
                candidate.stock_location_id
                or candidate.picking_type_id.default_location_src_id
            )
            if candidate_root and candidate_root.id == branch_root.id:
                branch_config_ids.append(candidate.id)

        return branch_config_ids or [config.id]

    def get_quarterly_inventory(self):
        """Return all storable POS products with branch qty-on-hand and per-month sales.

        The 3 months are the last completed calendar months immediately before
        the current month (e.g. on 2026-05-09 → Feb, Mar, Apr, each as
        [day 1, day 1 of next)).
        Each month's sales are returned as a separate field so the frontend
        can render 3 individual columns.

        Returns:
            {
                'month_names': ['Mes 1', 'Mes 2', 'Mes 3'],
                'products': list of dicts [{
                    'product_id': int,
                    'name': str,               # barcode-stripped product name
                    'vendor_code': str,         # first supplier product code or ''
                    'qty_on_hand': float,
                    'month1_sales': float,
                    'month2_sales': float,
                    'month3_sales': float,
                }]
            }
            Products sorted by total quarterly sales DESC (highest demand first).
        """
        self.ensure_one()
        config = self.config_id
        locations = config._get_branch_stock_locations()
        if not locations:
            return {'month_names': ['Mes 1', 'Mes 2', 'Mes 3'], 'products': []}

        # Reference date: today, anchored to full calendar months.
        # Sliding 30-day windows from session.start_at crossed month
        # boundaries and emptied the buckets — labels said "Feb/Mar/Abr"
        # but the queries hit the gaps in between, returning 0.
        today = fields.Date.context_today(self)
        current_month_start = today.replace(day=1)
        _MONTH_ES = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic',
        }
        month_boundaries = []
        month_names = []
        for i in range(3, 0, -1):  # oldest completed month to most recent completed month
            m_start = current_month_start - relativedelta(months=i)
            m_end = m_start + relativedelta(months=1)       # 1st of next month
            month_boundaries.append((m_start, m_end))
            month_names.append(f"{_MONTH_ES[m_start.month]} {m_start.year}")

        products = self.env['product.product'].search([
            ('available_in_pos', '=', True),
            ('is_storable', '=', True),
        ])
        if not products:
            return {'month_names': month_names, 'products': []}

        # --- Branch stock: single SQL query ---
        quant_groups = self.env['stock.quant']._read_group(
            domain=[
                ('product_id', 'in', products.ids),
                ('location_id', 'in', locations.ids),
                ('company_id', '=', config.company_id.id),
            ],
            groupby=['product_id'],
            aggregates=['quantity:sum'],
        )
        stock_by_product = {
            product.id: qty or 0.0
            for product, qty in quant_groups
        }

        # --- Per-month sales: 3 SQL queries (one per month) ---
        # Each query is bounded by product_id IN (...) and scoped to all POS
        # configs that share this branch's stock source, not to one cash drawer.
        # IMPORTANT: filter qty > 0 to exclude refund lines (POS refunds create
        # order lines with negative qty). We want gross sales, not net.
        branch_config_ids = self._get_branch_pos_config_ids()
        monthly_sales = [{}, {}, {}]  # index 0 = month1 (oldest)
        for idx, (m_start, m_end) in enumerate(month_boundaries):
            sales_groups = self.env['pos.order.line']._read_group(
                domain=[
                    ('product_id', 'in', products.ids),
                    ('order_id.config_id', 'in', branch_config_ids),
                    ('order_id.date_order', '>=', m_start),
                    ('order_id.date_order', '<', m_end),
                    ('order_id.state', 'in', ['done', 'invoiced', 'paid']),
                    ('qty', '>', 0),  # exclude refund lines
                ],
                groupby=['product_id'],
                aggregates=['qty:sum'],
            )
            monthly_sales[idx] = {
                product.id: qty or 0.0
                for product, qty in sales_groups
            }

        # --- Vendor codes: batch read from product.supplierinfo ---
        supplier_infos = self.env['product.supplierinfo'].sudo().search_read(
            domain=[
                ('product_id', 'in', products.ids),
            ],
            fields=['product_id', 'product_code'],
            order='sequence asc, id asc',
        )
        # Keep first (lowest sequence) supplier code per product
        vendor_code_by_product = {}
        for si in supplier_infos:
            pid = si['product_id'][0] if isinstance(si['product_id'], (list, tuple)) else si['product_id']
            if pid not in vendor_code_by_product and si.get('product_code'):
                vendor_code_by_product[pid] = si['product_code']

        # --- Also try product_tmpl_id-based supplier info for products without variant-level supplier ---
        tmpl_ids_missing = [
            p.product_tmpl_id.id for p in products
            if p.id not in vendor_code_by_product
        ]
        if tmpl_ids_missing:
            tmpl_supplier_infos = self.env['product.supplierinfo'].sudo().search_read(
                domain=[
                    ('product_tmpl_id', 'in', tmpl_ids_missing),
                    ('product_id', '=', False),
                ],
                fields=['product_tmpl_id', 'product_code'],
                order='sequence asc, id asc',
            )
            vendor_code_by_tmpl = {}
            for si in tmpl_supplier_infos:
                tmpl_id = si['product_tmpl_id'][0] if isinstance(si['product_tmpl_id'], (list, tuple)) else si['product_tmpl_id']
                if tmpl_id not in vendor_code_by_tmpl and si.get('product_code'):
                    vendor_code_by_tmpl[tmpl_id] = si['product_code']
            for p in products:
                if p.id not in vendor_code_by_product:
                    code = vendor_code_by_tmpl.get(p.product_tmpl_id.id)
                    if code:
                        vendor_code_by_product[p.id] = code

        result = []
        for p in products:
            line_id, line_name = self._get_product_x_line_value(p)
            result.append({
                'product_id': p.id,
                'name': _clean_product_name(p),
                'line_id': line_id,
                'line_name': line_name,
                'vendor_code': vendor_code_by_product.get(p.id, ''),
                'barcode': p.barcode or '',
                'qty_on_hand': stock_by_product.get(p.id, 0.0),
                'month1_sales': monthly_sales[0].get(p.id, 0.0),
                'month2_sales': monthly_sales[1].get(p.id, 0.0),
                'month3_sales': monthly_sales[2].get(p.id, 0.0),
            })
        # Sort by total quarterly sales DESC (sum of 3 months)
        result.sort(
            key=lambda r: r['month1_sales'] + r['month2_sales'] + r['month3_sales'],
            reverse=True,
        )

        # ── BF snapshot: fusionar el más reciente activo ──────────────
        bf_label = None
        bf_index = {}
        latest_snapshot = self.env['bi.pos.supplier.snapshot'].sudo().search(
            [('active', '=', True)],
            order='snapshot_date desc',
            limit=1,
        )
        if latest_snapshot:
            snap_date = latest_snapshot.snapshot_date
            _MONTH_ES_LABEL = {
                1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic',
            }
            bf_label = f"{snap_date.day} {_MONTH_ES_LABEL[snap_date.month]} {snap_date.year}"
            bf_index = latest_snapshot.get_pos_data()

        for item in result:
            bf_entry = (
                bf_index.get(item.get('barcode', ''))
                or bf_index.get((item.get('barcode', '') or '').lstrip('0'))
                or bf_index.get(f"vc_{item.get('vendor_code', '')}")
                or {}
            )
            item['bf_qty']    = bf_entry.get('qty_available')
            item['bf_cost']   = bf_entry.get('cost_price')
            item['bf_retail'] = bf_entry.get('retail_price')

        return {'month_names': month_names, 'bf_label': bf_label, 'products': result}

    def export_stock_xlsx(self, tab='inventory'):
        """Generate an Excel (.xlsx) export of the current stock tab.

        Uses the same data sources as the frontend tables:
          - tab='inventory' → get_quarterly_inventory()
          - tab='restock'   → get_replenishment_data()

        Returns:
            dict: {'filename': str, 'data': str (base64-encoded xlsx)}
        """
        self.ensure_one()
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            raise UserError(
                'El paquete openpyxl no está instalado. '
                'Ejecuta: pip install openpyxl'
            )

        wb = Workbook()
        ws = wb.active

        # ── Shared styles ─────────────────────────────────────────────
        header_font = Font(name='Calibri', bold=True, size=11, color='FFFFFF')
        header_fill = PatternFill(start_color='5A5290', end_color='5A5290', fill_type='solid')
        header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell_font = Font(name='Calibri', size=10)
        cell_align_left = Alignment(horizontal='left', vertical='center')
        cell_align_center = Alignment(horizontal='center', vertical='center')
        thin_border = Border(
            bottom=Side(style='thin', color='D0D0D0'),
        )
        # Alternating row fill
        even_fill = PatternFill(start_color='F5F3FA', end_color='F5F3FA', fill_type='solid')

        config_name = self.config_id.name or 'POS'
        session_date = (self.start_at or fields.Datetime.now()).strftime('%d/%m/%Y %H:%M')

        if tab == 'inventory':
            data = self.get_quarterly_inventory()
            month_names = data.get('month_names', ['Mes 1', 'Mes 2', 'Mes 3'])
            products = data.get('products', [])

            ws.title = 'Inventario General'
            columns = [
                ('Código', 16),
                ('Producto', 40),
                ('Línea', 18),
                ('Cód. Proveedor', 16),
                ('A la Mano', 12),
                (month_names[0] if len(month_names) > 0 else 'Mes 1', 12),
                (month_names[1] if len(month_names) > 1 else 'Mes 2', 12),
                (month_names[2] if len(month_names) > 2 else 'Mes 3', 12),
            ]

            # Title row
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(columns))
            title_cell = ws.cell(row=1, column=1,
                                 value=f'Inventario General — {config_name} — {session_date}')
            title_cell.font = Font(name='Calibri', bold=True, size=13, color='5A5290')
            title_cell.alignment = Alignment(horizontal='left', vertical='center')
            ws.row_dimensions[1].height = 28

            # Header row
            for col_idx, (col_name, col_width) in enumerate(columns, start=1):
                cell = ws.cell(row=3, column=col_idx, value=col_name)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_align
                ws.column_dimensions[cell.column_letter].width = col_width

            # Data rows
            for row_idx, p in enumerate(products, start=4):
                row_data = [
                    p.get('barcode', ''),
                    p.get('name', ''),
                    p.get('line_name', ''),
                    p.get('vendor_code', ''),
                    p.get('qty_on_hand', 0),
                    p.get('month1_sales', 0),
                    p.get('month2_sales', 0),
                    p.get('month3_sales', 0),
                ]
                for col_idx, value in enumerate(row_data, start=1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.font = cell_font
                    cell.alignment = cell_align_center if col_idx >= 4 else cell_align_left
                    cell.border = thin_border
                    if row_idx % 2 == 0:
                        cell.fill = even_fill

            filename = f'inventario_{config_name}_{session_date.replace("/", "-").replace(" ", "_").replace(":", "")}.xlsx'

        else:  # tab == 'restock'
            products = self.get_replenishment_data()

            ws.title = 'Por Reabastecer'
            restock_fill = PatternFill(start_color='71639E', end_color='71639E', fill_type='solid')
            columns = [
                ('Código', 16),
                ('Producto', 40),
                ('A la mano', 12),
                ('Mín', 10),
                ('Máx', 10),
                ('Por ordenar', 14),
            ]

            # Title row
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(columns))
            title_cell = ws.cell(row=1, column=1,
                                 value=f'Por Reabastecer — {config_name} — {session_date}')
            title_cell.font = Font(name='Calibri', bold=True, size=13, color='71639E')
            title_cell.alignment = Alignment(horizontal='left', vertical='center')
            ws.row_dimensions[1].height = 28

            # Header row
            for col_idx, (col_name, col_width) in enumerate(columns, start=1):
                cell = ws.cell(row=3, column=col_idx, value=col_name)
                cell.font = header_font
                cell.fill = restock_fill
                cell.alignment = header_align
                ws.column_dimensions[cell.column_letter].width = col_width

            # Data rows
            for row_idx, p in enumerate(products, start=4):
                row_data = [
                    p.get('barcode', ''),
                    p.get('display_name', ''),
                    p.get('qty_on_hand', 0),
                    p.get('product_min_qty', 0),
                    p.get('product_max_qty', 0),
                    p.get('qty_to_order', 0),
                ]
                for col_idx, value in enumerate(row_data, start=1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.font = cell_font
                    cell.alignment = cell_align_center if col_idx >= 3 else cell_align_left
                    cell.border = thin_border
                    if row_idx % 2 == 0:
                        cell.fill = even_fill

            filename = f'reabastecimiento_{config_name}_{session_date.replace("/", "-").replace(" ", "_").replace(":", "")}.xlsx'

        # ── Serialize to base64 ───────────────────────────────────────
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        b64_data = base64.b64encode(buffer.read()).decode('utf-8')
        buffer.close()

        return {'filename': filename, 'data': b64_data}

    def create_inventory_replenishment(self, product_id, qty):
        """Create an internal transfer from the Matrix warehouse to this POS location.

        'Matrix' is the company's primary warehouse — identified as the one with
        the lowest ID for this company (i.e. the first warehouse ever created).

        Args:
            product_id (int): product.product record ID.
            qty (float): quantity to request. Defaults to 1 if <= 0.

        Returns:
            {'success': True,  'picking_id': int, 'picking_name': str, 'product_name': str, 'qty': float}
            {'success': False, 'message': str}
        """
        self.ensure_one()
        config = self.config_id

        product = self.env['product.product'].browse(product_id)
        if not product.exists():
            return {'success': False, 'message': _('Producto no encontrado.')}

        qty = float(qty or 1.0)
        if qty <= 0:
            qty = 1.0

        # Matrix = first warehouse (lowest ID) for this company.
        # sudo() bypasses ir.rule multi-company filtering: the Matrix warehouse
        # may belong to a different company than the user's active one.
        matrix_warehouse = self.env['stock.warehouse'].sudo().search(
            [('company_id', '=', config.company_id.id)],
            order='id asc',
            limit=1,
        )
        if not matrix_warehouse:
            return {
                'success': False,
                'message': _('No se encontró almacén principal (Matriz) para esta empresa.'),
            }

        src_location = matrix_warehouse.lot_stock_id
        dest_location = config.picking_type_id.default_location_dest_id
        if not dest_location:
            return {
                'success': False,
                'message': _('La caja POS no tiene ubicación de destino configurada.'),
            }

        if src_location == dest_location:
            return {
                'success': False,
                'message': _(
                    'La Matriz y esta sucursal comparten la misma ubicación (%s). '
                    'Verifica la configuración del tipo de operación.',
                    src_location.complete_name,
                ),
            }

        internal_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', matrix_warehouse.id),
            ('code', '=', 'internal'),
        ], limit=1)
        if not internal_type:
            return {
                'success': False,
                'message': _(
                    'No se encontró tipo de operación interna para la Matriz ("%s").',
                    matrix_warehouse.name,
                ),
            }

        picking = self.env['stock.picking'].sudo().create({
            'picking_type_id': internal_type.id,
            'location_id': src_location.id,
            'location_dest_id': dest_location.id,
            'origin': _('POS Solicitud Inventario - %(pos)s', pos=config.name),
            'move_ids': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'location_id': src_location.id,
                'location_dest_id': dest_location.id,
            })],
        })

        _logger.info(
            "POS '%s': inventory replenishment %s created for '%s' "
            "(qty=%.2f, %s → %s).",
            config.name, picking.name, product.display_name,
            qty, src_location.complete_name, dest_location.complete_name,
        )

        return {
            'success': True,
            'picking_id': picking.id,
            'picking_name': picking.name,
            'qty': qty,
            'product_name': product.display_name,
        }

    # -------------------------------------------------------------------------
    # Feature: E-commerce Orders Screen
    # -------------------------------------------------------------------------

    def get_ecommerce_orders(self):
        """Return pending e-commerce (website) orders for this branch's warehouse.

        An order is considered 'pending' when state = 'sale' (confirmed but not yet
        fully delivered/invoiced). Branch assignment is via warehouse_id on the
        sale.order matching this POS config's warehouse.

        Returns [] gracefully if the website_sale module is not installed.

        Returns:
            list of dicts [{
                'id': int,
                'name': str,
                'partner_name': str,
                'amount_total': float,
                'date_order': str,   # formatted dd/mm/yyyy HH:MM
                'product_count': int,
            }]
        """
        self.ensure_one()

        SaleOrder = self.env['sale.order']
        # Graceful degradation: e-commerce field may not exist without website_sale
        if 'website_id' not in SaleOrder._fields:
            return []

        warehouse = self.config_id.picking_type_id.warehouse_id
        if not warehouse:
            return []

        orders = SaleOrder.search_read(
            domain=[
                ('website_id', '!=', False),
                ('warehouse_id', '=', warehouse.id),
                ('state', '=', 'sale'),
            ],
            fields=['id', 'name', 'partner_id', 'amount_total', 'date_order'],
            order='date_order desc',
            limit=50,
        )

        for order in orders:
            # product count via a single search_count per order
            order['product_count'] = self.env['sale.order.line'].search_count([
                ('order_id', '=', order['id']),
            ])
            # Flatten Many2one tuple to string
            partner = order.pop('partner_id', None)
            order['partner_name'] = partner[1] if isinstance(partner, (list, tuple)) else str(partner or 'Desconocido')
            # Format datetime for display
            dt = order.get('date_order')
            order['date_order'] = dt.strftime('%d/%m/%Y %H:%M') if dt else ''

        return orders


class ProductProduct(models.Model):
    """CONSOLIDATED: Removed duplicate _load_pos_data_fields override.

    The original bi_pos_session.py defined a second ProductProduct class
    that duplicated fields already declared in bi_pos_stock.py. In Python's MRO,
    having two _inherit classes for the same model in the same module causes
    the second definition to silently override the first, producing unpredictable
    field lists depending on import order.

    The single canonical _load_pos_data_fields is now in bi_pos_stock.py.
    This class only adds the _load_pos_data_fields in bi_pos_session context
    if there were session-specific fields needed — currently there are none.
    """
    _inherit = 'product.product'
    # Intentionally empty: consolidation complete, no session-specific fields needed.


class StockLocation(models.Model):
    _inherit = 'stock.location'

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Only expose the minimum safe fields needed for display purposes."""
        return ['id', 'name', 'complete_name', 'usage']

    @api.model
    def _load_pos_data_search_read(self, data, config):
        """FIXED SECURITY FLAW: Original used self.search([]) with no filters.

        The original implementation sent ALL stock locations from ALL companies
        and ALL warehouses to the browser. This exposed location hierarchies
        of other branches.

        Now only sends locations that belong to the requesting POS's warehouse,
        scoped to its company. The frontend needs location names only for
        optional display; all stock computation is already done server-side.
        """
        locations = config._get_branch_stock_locations()
        if not locations:
            return []
        return locations.read(self._load_pos_data_fields(config))

    @api.model
    def _load_pos_data_domain(self, data):
        # Domain is overridden by _load_pos_data_search_read above.
        # Kept as a pass-through to satisfy the base interface contract.
        return []
