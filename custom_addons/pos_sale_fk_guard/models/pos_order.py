# -*- coding: utf-8 -*-
# Part of Medicine Depot. See LICENSE file for full copyright and licensing details.

"""
Defensive guard against stale ``sale_order_line_id`` references sent by the
POS frontend from its offline IndexedDB cache.

Scenario (real-world reproduction):
  1. A Sales Order with a "Store Pickup" service line is loaded into the POS.
  2. While the POS is operating offline, a backend user deletes or modifies
     that service line from the Sales Order.
  3. The POS eventually syncs its cached order. The payload still contains the
     now-orphan ``sale_order_line_id``.
  4. ``pos.order.create()`` triggers an INSERT on ``pos_order_line`` with the
     stale FK → PostgreSQL raises:
       IntegrityError: insert or update on table "pos_order_line" violates
       foreign key constraint "pos_order_line_sale_order_line_id_fkey"
  5. The *entire* transaction — ticket, payments, picking — is rolled back.
     The cashier sees an HTTP 500 and must retry, often repeatedly.

Fix:
  Before the ORM touches the database we scan every order-line dict in the
  incoming payload. Any ``sale_order_line_id`` that does not exist in
  ``sale.order.line`` is silently nullified. The companion field
  ``sale_order_origin_id`` is cleaned up the same way.

  A warning is logged with the full details so the operations team can
  investigate the root-cause (stale POS cache, deleted SO lines, etc.).
"""

import logging

from odoo import api, models
from odoo.fields import Command

_logger = logging.getLogger(__name__)

# Fields on pos.order.line that hold FK references to sale.order / sale.order.line.
# Each entry: (field_name, target_model)
_SALE_FK_FIELDS = [
    ('sale_order_line_id', 'sale.order.line'),
    ('sale_order_origin_id', 'sale.order'),
]


class PosOrder(models.Model):
    _inherit = 'pos.order'

    # ------------------------------------------------------------------
    # Public API override
    # ------------------------------------------------------------------

    @api.model
    def _process_order(self, order, existing_order):
        """Sanitise sale-related FK references before the ORM INSERT.

        We intercept the payload *before* ``super()._process_order`` calls
        ``self.create()`` (for new orders) or ``self.write()`` (for existing
        drafts).  The mutation is performed **in-place** on the ``order``
        dict so every downstream consumer sees clean data.
        """
        self._sanitize_sale_fk_references(order)
        return super()._process_order(order, existing_order)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @api.model
    def _sanitize_sale_fk_references(self, order):
        """Validate and clean stale sale FK IDs in order-line commands.

        The ``lines`` key in the order dict contains ORM write-command
        tuples.  We only need to inspect ``Command.CREATE`` (0) and
        ``Command.UPDATE`` (1) since those are the ones that carry a
        values dict.

        Modifies ``order`` **in place** — returns nothing.
        """
        lines = order.get('lines')
        if not lines:
            return

        # Collect all referenced IDs across every line for a single SQL
        # round-trip instead of one query per line.
        ids_to_check = {}  # {model_name: {id, ...}}
        line_refs = []      # [(line_vals, field_name, model_name, ref_id), ...]

        for line_cmd in lines:
            # ORM command format: (command_code, id_or_0, {vals})
            if not isinstance(line_cmd, (list, tuple)) or len(line_cmd) < 3:
                continue
            cmd_code = line_cmd[0]
            if cmd_code not in (Command.CREATE, Command.UPDATE):
                continue

            vals = line_cmd[2]
            if not isinstance(vals, dict):
                continue

            for field_name, model_name in _SALE_FK_FIELDS:
                ref_id = vals.get(field_name)
                if ref_id:
                    ids_to_check.setdefault(model_name, set()).add(ref_id)
                    line_refs.append((vals, field_name, model_name, ref_id))

        if not ids_to_check:
            return  # nothing to validate

        # Batch-check existence: one query per target model (typically 1–2).
        existing_ids = {}  # {model_name: {id, ...}}
        for model_name, ref_ids in ids_to_check.items():
            existing = self.env[model_name].browse(list(ref_ids)).exists()
            existing_ids[model_name] = set(existing.ids)

        # Nullify orphan references.
        order_ref = order.get('name') or order.get('uuid', '???')
        for vals, field_name, model_name, ref_id in line_refs:
            if ref_id not in existing_ids.get(model_name, set()):
                _logger.warning(
                    "POS FK Guard: Order '%s' — line field '%s' referenced "
                    "%s(id=%s) which no longer exists. Setting to False to "
                    "prevent FK violation.",
                    order_ref, field_name, model_name, ref_id,
                )
                vals[field_name] = False
