def migrate(cr, version):
    """Upgrade: rellena lot_expiration_date desde stock.lot para líneas
    existentes. Cubre el caso de upgrade desde v0.0.6 (related store=False)
    donde la columna no existía o estaba vacía."""
    cr.execute("""
        UPDATE purchase_order_line pol
        SET lot_expiration_date = sl.expiration_date
        FROM stock_lot sl
        WHERE pol.lot_id = sl.id
          AND pol.lot_expiration_date IS NULL
          AND sl.expiration_date IS NOT NULL
    """)
