# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


class PosOrderLine(models.Model):
    """Extend get_existing_lots() to include expiration_date and sort FEFO.

    The standard method returns {id, name, product_qty} per lot.
    We add 'expiration_date' (ISO string or null) and re-sort so that the lot
    expiring soonest is always first — Sell First what Expires First (FEFO).

    Gracefully degrades if the product_expiry module is not installed
    (expiration_date field absent from stock.lot).
    """
    _inherit = 'pos.order.line'

    @api.model
    def get_existing_lots(self, company_id, config_id, product_id):
        """Override: adds expiration_date to each lot dict and applies FEFO sort."""
        result = super().get_existing_lots(company_id, config_id, product_id)

        lot_ids = [r['id'] for r in result if r.get('id')]
        has_expiry = 'expiration_date' in self.env['stock.lot']._fields

        if lot_ids and has_expiry:
            lots = self.env['stock.lot'].sudo().browse(lot_ids)
            expiry_by_id = {}
            for lot in lots:
                exp = lot.expiration_date
                expiry_by_id[lot.id] = exp.strftime('%Y-%m-%dT%H:%M:%SZ') if exp else None
            for r in result:
                r['expiration_date'] = expiry_by_id.get(r['id'])
        else:
            for r in result:
                r['expiration_date'] = None

        # FEFO sort: lots with the earliest (non-null) expiry first; null dates last.
        result.sort(key=lambda r: (r['expiration_date'] is None, r['expiration_date'] or ''))
        return result


class PosSession(models.Model):
    """Add lot expiry data to POS session RPC surface.

    Two public methods:
      - get_lots_expiry_summary()  — called once at session open to populate the
                                     expiry badge on every ProductCard.
      - get_product_lots_detail()  — called on-demand when the cashier opens the
                                     LotDetailPopup for a specific product.
    """
    _inherit = 'pos.session'

    def get_lots_expiry_summary(self):
        """Return the nearest-expiry lot per tracked product in this branch.

        Only includes products with lot/serial tracking that have at least one
        quant with qty > 0 in the branch locations.

        IMPORTANT — keyed by product.template.id, not product.product.id.
        In the POS frontend, `productsToDisplay` iterates product.template
        records, so `product.id` in templates / XPath expressions is the
        template ID.  Using template IDs here keeps the JS lookup consistent.

        Returns:
            dict: {str(template_id): {
                'lot_name': str,
                'expiration_date': str | None,   # ISO UTC string
                'qty': float,
            }}
        """
        self.ensure_one()
        config = self.config_id
        locations = config._get_branch_stock_locations()
        if not locations:
            return {}

        has_expiry = 'expiration_date' in self.env['stock.lot']._fields

        # OPTIMIZED: search_read returns only needed fields — no full ORM objects loaded.
        # Previously: search() loaded all quant fields + lazy-loaded product_tmpl_id
        # and lot.expiration_date on every iteration (hidden N+1 queries).
        products_data = self.env['product.product'].search_read(
            domain=[
                ('available_in_pos', '=', True),
                ('is_storable', '=', True),
                ('tracking', 'in', ['lot', 'serial']),
            ],
            fields=['id', 'product_tmpl_id'],
        )
        if not products_data:
            return {}

        product_ids = [p['id'] for p in products_data]
        tmpl_by_product = {p['id']: p['product_tmpl_id'][0] for p in products_data}

        quants_data = self.env['stock.quant'].sudo().search_read(
            domain=[
                ('product_id', 'in', product_ids),
                ('location_id', 'in', locations.ids),
                ('lot_id', '!=', False),
                ('quantity', '>', 0),
            ],
            fields=['product_id', 'lot_id', 'quantity'],
        )
        if not quants_data:
            return {}

        # Batch-load expiry dates in ONE query instead of N lazy loads
        lot_ids = list({q['lot_id'][0] for q in quants_data})
        expiry_by_lot = {}
        if has_expiry and lot_ids:
            lots_data = self.env['stock.lot'].sudo().search_read(
                domain=[('id', 'in', lot_ids)],
                fields=['id', 'expiration_date'],
            )
            for ld in lots_data:
                exp = ld.get('expiration_date')
                expiry_by_lot[ld['id']] = (
                    exp.strftime('%Y-%m-%dT%H:%M:%SZ') if exp else None
                )

        # Group lots by product.template.id — pure dict lookups, no ORM traversal
        by_template = {}
        for q in quants_data:
            pid = q['product_id'][0]
            lid = q['lot_id'][0]
            lname = q['lot_id'][1]
            tmpl_id = tmpl_by_product.get(pid)
            if not tmpl_id:
                continue
            entry = {
                'lot_name': lname,
                'expiration_date': expiry_by_lot.get(lid),
                'qty': q['quantity'],
            }
            by_template.setdefault(tmpl_id, []).append(entry)

        # Per template: keep only the nearest-expiry lot (FEFO front-runner)
        result = {}
        for tmpl_id, lots in by_template.items():
            lots.sort(key=lambda l: (l['expiration_date'] is None, l['expiration_date'] or ''))
            result[str(tmpl_id)] = lots[0]

        _logger.debug(
            "[bi_pos_stock] get_lots_expiry_summary: %d tracked templates with lots.",
            len(result),
        )
        return result

    def get_product_lots_detail(self, product_id):
        """Return ALL lots for a product in this branch, sorted FEFO.

        Called on-demand when the cashier opens the LotDetailPopup.

        Args:
            product_id (int): product.template.id  (the POS frontend passes
                template IDs because productsToDisplay iterates product.template
                records).  We resolve all variants internally.

        Returns:
            list of dicts: [{
                'lot_id': int,
                'lot_name': str,
                'expiration_date': str | None,
                'qty': float,
            }]  — sorted by expiration_date ASC (nearest first), null last.
        """
        self.ensure_one()
        config = self.config_id
        locations = config._get_branch_stock_locations()
        if not locations:
            return []

        has_expiry = 'expiration_date' in self.env['stock.lot']._fields

        # product_id is a template ID — resolve all product.product variants
        template = self.env['product.template'].browse(product_id)
        variant_ids = template.product_variant_ids.ids if template.exists() else [product_id]

        quants = self.env['stock.quant'].sudo().search([
            ('product_id', 'in', variant_ids),
            ('location_id', 'in', locations.ids),
            ('lot_id', '!=', False),
            ('quantity', '>', 0),
        ])

        # Aggregate qty per lot (a product may have quants in multiple sub-locations)
        by_lot = {}
        for q in quants:
            lid = q.lot_id.id
            if lid not in by_lot:
                exp = None
                if has_expiry and q.lot_id.expiration_date:
                    exp = q.lot_id.expiration_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                by_lot[lid] = {
                    'lot_id': lid,
                    'lot_name': q.lot_id.name,
                    'expiration_date': exp,
                    'qty': 0.0,
                }
            by_lot[lid]['qty'] += q.quantity

        result = list(by_lot.values())
        result.sort(key=lambda r: (r['expiration_date'] is None, r['expiration_date'] or ''))
        return result

    def get_all_lot_details(self):
        """Return a flat dict of every available lot for all tracked POS products.

        Key format: "{product_id}_{lot_name}" → {product_id, expiration_date, qty}

        Used by ProductCard to instantly look up the selected lot's expiry and
        available qty after the cashier picks a specific lot — O(1) client-side
        lookup without a second RPC call.

        Returns:
            dict: { "123_LOT001": {
                'product_id': int,
                'expiration_date': str | None,   # ISO UTC string
                'qty': float,
            }, ... }
        """
        self.ensure_one()
        config = self.config_id
        locations = config._get_branch_stock_locations()
        if not locations:
            return {}

        has_expiry = 'expiration_date' in self.env['stock.lot']._fields

        # OPTIMIZED: same pattern as get_lots_expiry_summary — search_read + batch expiry load.
        products_data = self.env['product.product'].search_read(
            domain=[
                ('available_in_pos', '=', True),
                ('is_storable', '=', True),
                ('tracking', 'in', ['lot', 'serial']),
            ],
            fields=['id'],
        )
        if not products_data:
            return {}

        product_ids = [p['id'] for p in products_data]

        quants_data = self.env['stock.quant'].sudo().search_read(
            domain=[
                ('product_id', 'in', product_ids),
                ('location_id', 'in', locations.ids),
                ('lot_id', '!=', False),
                ('quantity', '>', 0),
            ],
            fields=['product_id', 'lot_id', 'quantity'],
        )
        if not quants_data:
            return {}

        # Batch-load expiry dates in ONE query
        lot_ids = list({q['lot_id'][0] for q in quants_data})
        expiry_by_lot = {}
        if has_expiry and lot_ids:
            lots_data = self.env['stock.lot'].sudo().search_read(
                domain=[('id', 'in', lot_ids)],
                fields=['id', 'expiration_date'],
            )
            for ld in lots_data:
                exp = ld.get('expiration_date')
                expiry_by_lot[ld['id']] = (
                    exp.strftime('%Y-%m-%dT%H:%M:%SZ') if exp else None
                )

        # Aggregate qty per (product_id, lot_name) — pure dict lookups, no ORM traversal
        by_key = {}
        for q in quants_data:
            pid = q['product_id'][0]
            lid = q['lot_id'][0]
            lname = q['lot_id'][1]
            key = f"{pid}_{lname}"
            if key not in by_key:
                by_key[key] = {
                    'product_id': pid,
                    'expiration_date': expiry_by_lot.get(lid),
                    'qty': 0.0,
                }
            by_key[key]['qty'] += q['quantity']

        _logger.debug(
            "[bi_pos_stock] get_all_lot_details: %d lot entries across %d products.",
            len(by_key),
            len({v['product_id'] for v in by_key.values()}),
        )
        return by_key
