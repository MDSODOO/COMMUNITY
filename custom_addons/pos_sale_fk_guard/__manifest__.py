{
    "name": "POS Sale FK Guard",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": (
        "Prevents ForeignKey crashes when POS sends stale sale_order_line_id "
        "references from its offline cache."
    ),
    "description": """
        Defensive patch for the pos_sale bridge.

        Problem:
          When a Sales Order line (e.g. "Store Pickup" service) is deleted or
          modified in the backend while the POS is operating offline, the POS
          frontend keeps the now-orphan sale_order_line_id in its local cache.
          On sync, the ORM's INSERT triggers a PostgreSQL FK violation
          (pos_order_line_sale_order_line_id_fkey) and the entire transaction
          — including the ticket and all payments — is rolled back.

        Solution:
          Override ``_process_order`` on pos.order to scan every order-line dict
          in the incoming payload.  If a ``sale_order_line_id`` is present, we
          validate it exists in ``sale.order.line``.  Orphan IDs are silently
          set to ``False`` so the ticket can still be saved.  A server log
          warning is emitted for traceability.

        This module has NO frontend assets, NO views, and NO data files.
        It can be uninstalled without side-effects once the root-cause
        (offline cache staleness) is addressed in a future POS release.
    """,
    "author": "Medicine Depot - Daniel Cervera",
    "depends": ["pos_sale"],
    "data": [],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
