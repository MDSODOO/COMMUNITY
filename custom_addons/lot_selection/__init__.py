from . import models


def _post_init_hook(env):
    """Pobla lot_expiration_date desde stock.lot.expiration_date en líneas
    existentes al instalar el módulo por primera vez."""
    env.cr.execute("""
        UPDATE purchase_order_line pol
        SET lot_expiration_date = sl.expiration_date
        FROM stock_lot sl
        WHERE pol.lot_id = sl.id
          AND pol.lot_expiration_date IS NULL
          AND sl.expiration_date IS NOT NULL
    """)
