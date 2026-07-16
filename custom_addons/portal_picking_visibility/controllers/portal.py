import logging

from odoo import _, http
from odoo.http import request
from odoo.fields import Domain
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.sale.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)


class PortalPickingVisibility(CustomerPortal):
    """Extiende la visibilidad de órdenes en /my/orders y añade /my/pickings.

    FUNCIONALIDADES
    ───────────────
    1. /my/orders: amplia el domain para mostrar órdenes done, sent (e-commerce),
       y órdenes con pickings activos.
    2. /my/pickings: lista paginada de albaranes (outgoing + incoming con sale_id),
       con filtros por estado y sorting.
    3. /my/pickings/<id>: detalle del albarán, líneas de movimiento, tracking.
    4. Card en /my: contador "Mis Entregas".
    """

    def _prepare_orders_domain(self, partner):
        base_domain = super()._prepare_orders_domain(partner)

        partner_domain = [
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
        ]

        expanded_state_domain = Domain.OR([
            [('state', '=', 'sale')],
            [('state', '=', 'done')],
            [('state', '=', 'sent'), ('website_id', '!=', False)],
            [('has_active_pickings', '=', True)],
        ])

        return Domain.AND([base_domain, partner_domain, expanded_state_domain])

    def _prepare_pickings_domain(self, partner):
        """Domain hermético para pickings del usuario portal.

        Incluye:
        - Entregas salientes (outgoing) al cliente
        - Devoluciones entrantes (incoming) vinculadas a una venta

        Excluye:
        - Recepciones de compra (sin sale_id)
        - Operaciones internas de almacén
        - Pickings en draft o cancelados
        """
        return [
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
            ('picking_type_code', 'in', ['outgoing', 'incoming']),
            ('sale_id', '!=', False),
            ('state', 'not in', ['draft', 'cancel']),
        ]

    def _prepare_home_portal_values(self, counters):
        """Añade contador de albaranes a la tarjeta de inicio /my."""
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if 'picking_count' in counters:
            domain = self._prepare_pickings_domain(partner)
            values['picking_count'] = request.env['stock.picking'].sudo().search_count(domain)
        return values

    @http.route(
        ['/my/pickings', '/my/pickings/page/<int:page>'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_my_pickings(self, page=1, sortby='date', filterby='all', **kw):
        """Lista paginada de albaranes del usuario portal."""
        partner = request.env.user.partner_id
        domain = self._prepare_pickings_domain(partner)

        searchbar_sortings = {
            'date': {'label': _('Fecha programada'), 'order': 'scheduled_date desc'},
            'name': {'label': _('Referencia'), 'order': 'name asc'},
            'state': {'label': _('Estado'), 'order': 'state asc'},
        }

        searchbar_filters = {
            'all': {'label': _('Todos'), 'domain': []},
            'ready': {'label': _('Listo para enviar'), 'domain': [('state', '=', 'assigned')]},
            'done': {'label': _('Entregado'), 'domain': [('state', '=', 'done')]},
            'in_progress': {
                'label': _('En progreso'),
                'domain': [('state', 'in', ['confirmed', 'waiting'])],
            },
        }

        domain += searchbar_filters.get(filterby, searchbar_filters['all'])['domain']
        sortby_order = searchbar_sortings.get(sortby, searchbar_sortings['date'])['order']

        # sudo() requerido: stock.picking tiene ACL de lectura para portal (ir.model.access),
        # pero no hay ir.rules que restrinjan por partner; sin sudo() el domain aplicado
        # aquí filtra correctamente, pero los campos de stock podrían requerir escalada.
        Picking = request.env['stock.picking'].sudo()
        picking_count = Picking.search_count(domain)
        pager = portal_pager(
            url='/my/pickings',
            total=picking_count,
            page=page,
            step=self._items_per_page,
            url_args={'sortby': sortby, 'filterby': filterby},
        )
        pickings = Picking.search(
            domain,
            order=sortby_order,
            limit=self._items_per_page,
            offset=pager['offset'],
        )

        return request.render(
            'portal_picking_visibility.portal_my_pickings',
            {
                'pickings': pickings,
                'page_name': 'picking',
                'pager': pager,
                'default_url': '/my/pickings',
                'searchbar_sortings': searchbar_sortings,
                'sortby': sortby,
                'searchbar_filters': searchbar_filters,
                'filterby': filterby,
            },
        )

    @http.route(['/my/pickings/<int:picking_id>'], type='http', auth='user', website=True)
    def portal_picking_page(self, picking_id, **kw):
        """Detalle de un albarán con validación de acceso por partner."""
        partner = request.env.user.partner_id
        domain = self._prepare_pickings_domain(partner) + [('id', '=', picking_id)]
        picking_sudo = request.env['stock.picking'].sudo().search(domain, limit=1)
        if not picking_sudo:
            return request.not_found()

        return request.render(
            'portal_picking_visibility.portal_my_picking_detail',
            {
                'stock_picking': picking_sudo,
                'page_name': 'picking_detail',
            },
        )
