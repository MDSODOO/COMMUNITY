from . import models
from . import controllers


def _post_init_compute_delivery_status(env):
    """Recalcula portal_delivery_status para todas las órdenes existentes.

    Al instalar el módulo por primera vez, los campos stored compute
    (portal_delivery_status, has_active_pickings, etc.) están vacíos para
    los registros que ya existían en la BD. Este hook los recalcula de
    forma masiva usando SQL directo + ORM batch para evitar timeouts.
    """
    # Buscar órdenes que tengan al menos un picking outgoing
    orders_with_pickings = env['sale.order'].sudo().search([
        ('picking_ids', '!=', False),
    ])
    if orders_with_pickings:
        # Forzar recálculo en batches de 500 para evitar memory pressure
        batch_size = 500
        for i in range(0, len(orders_with_pickings), batch_size):
            batch = orders_with_pickings[i:i + batch_size]
            batch._compute_portal_delivery_status()
        # Flush explícito para persistir los valores store=True
        env.flush_all()
