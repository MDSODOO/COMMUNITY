from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _description = 'Sale Order (portal delivery status extensions)'

    # ── Campos computados almacenados ─────────────────────────────────
    # store=True para:
    #   1. Performance: search() en /my/orders sin compute por registro.
    #   2. Indexable: domain directo sin sub-query.
    #
    # portal_delivery_status_label es store=False con compute propio para
    # evitar llamar _() durante el upgrade (sin contexto de idioma activo).
    # ──────────────────────────────────────────────────────────────────
    portal_delivery_status = fields.Selection(
        selection=[
            ('no_delivery', 'Sin envío'),
            ('pending',     'Preparando'),
            ('confirmed',   'Confirmado'),
            ('ready',       'Listo para enviar'),
            ('partial',     'Parcialmente entregado'),
            ('delivered',   'Entregado'),
            ('cancelled',   'Cancelado'),
        ],
        string="Estado de envío (Portal)",
        compute='_compute_portal_delivery_status',
        store=True,
        default='no_delivery',
        help=(
            "Estado consolidado de los albaranes vinculados a esta orden. "
            "Visible para el cliente en el portal /my/orders."
        ),
    )

    portal_delivery_status_label = fields.Char(
        string="Etiqueta de envío",
        compute='_compute_portal_delivery_status_label',
        store=False,
        help="Etiqueta legible del estado de envío para mostrar en el portal.",
    )

    portal_delivery_badge_class = fields.Char(
        string="Clase CSS del badge",
        compute='_compute_portal_delivery_status',
        store=True,
        help="Clase Bootstrap para el badge de estado de envío en el portal.",
    )

    has_active_pickings = fields.Boolean(
        string="Tiene albaranes activos",
        compute='_compute_portal_delivery_status',
        store=True,
        help=(
            "True si la orden tiene al menos un picking en estado "
            "confirmed, assigned o done. Usado en el domain del portal."
        ),
    )

    _STATUS_LABELS = {
        'no_delivery': 'Sin envío',
        'pending':     'Preparando',
        'confirmed':   'Confirmado',
        'ready':       'Listo para enviar',
        'partial':     'Parcialmente entregado',
        'delivered':   'Entregado',
        'cancelled':   'Cancelado',
    }

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_portal_delivery_status(self):
        """Calcula el estado consolidado de envío a partir de los pickings.

        Lógica de consolidación (prioridad descendente):
          1. Sin pickings → 'no_delivery'
          2. Todos cancelados → 'cancelled'
          3. Todos entregados (done) → 'delivered'
          4. Alguno done + alguno no-done → 'partial'
          5. Alguno assigned → 'ready'
          6. Alguno confirmed → 'confirmed'
          7. Solo drafts/waiting → 'pending'
        """
        for order in self:
            pickings = order.picking_ids.filtered(
                lambda p: p.picking_type_code == 'outgoing'
            )

            if not pickings:
                order.portal_delivery_status = 'no_delivery'
                order.portal_delivery_badge_class = 'secondary'
                order.has_active_pickings = False
                continue

            states = set(pickings.mapped('state'))
            non_cancel = states - {'cancel'}

            if not non_cancel:
                status, badge, has_active = 'cancelled', 'secondary', False
            elif non_cancel == {'done'}:
                status, badge, has_active = 'delivered', 'success', True
            elif 'done' in non_cancel and non_cancel - {'done'}:
                status, badge, has_active = 'partial', 'warning', True
            elif 'assigned' in non_cancel:
                status, badge, has_active = 'ready', 'info', True
            elif 'confirmed' in non_cancel:
                status, badge, has_active = 'confirmed', 'info', True
            else:
                status, badge, has_active = 'pending', 'warning', True

            order.portal_delivery_status = status
            order.portal_delivery_badge_class = badge
            order.has_active_pickings = has_active

    @api.depends('portal_delivery_status')
    def _compute_portal_delivery_status_label(self):
        for order in self:
            order.portal_delivery_status_label = _(
                self._STATUS_LABELS.get(order.portal_delivery_status, '')
            )
