from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import http, fields
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


def _branch_warehouse_id():
    """Almacen de la sucursal asignada al cliente autenticado, si aplica.

    La sucursal vive en el campo Studio ``res.partner.x_studio_branch_office``,
    que segun la base puede ser many2one a ``stock.warehouse``, char/text con el
    nombre, o selection. Se cubren los tres casos. Devuelve None para el visitante
    publico o cuando la sucursal no resuelve a un almacen activo.
    """
    user = request.env.user
    if not user or user._is_public():
        return None

    partner = user.partner_id.sudo()
    field = partner._fields.get('x_studio_branch_office')
    if not field:
        return None

    value = partner.x_studio_branch_office
    if not value:
        return None

    Warehouse = request.env['stock.warehouse'].sudo()

    # many2one directo a stock.warehouse: el valor ya es el almacen.
    if field.type == 'many2one' and getattr(field, 'comodel_name', '') == 'stock.warehouse':
        return value.id or None

    # char / text / selection / m2o a otro modelo: resolver por nombre.
    name = value.display_name if hasattr(value, 'display_name') else str(value)
    name = (name or '').strip().lower()
    if not name:
        return None

    warehouse = Warehouse.search([('active', '=', True)]).filtered(
        lambda w: (w.display_name or '').strip().lower() == name
        or (w.name or '').strip().lower() == name
    )[:1]
    return warehouse.id or None


def resolve_warehouse():
    """Return the warehouse id to use for stock queries.

    Priority:
      1. Sucursal del cliente autenticado (res.partner.x_studio_branch_office)
      2. website.warehouse_id  (set when website_sale_stock is installed)
      3. First warehouse of the current company (fallback)

    Returns None for public (anonymous) users — callers must treat this as
    qty=0 (B2B-only store requirement).
    """
    # B2B-only: public visitors never receive stock data.
    if not request.env.user or request.env.user._is_public():
        return None

    wh_id = _branch_warehouse_id()
    if wh_id:
        return wh_id

    try:
        # sudo() prevents AccessError for public/portal users who lack
        # stock.warehouse read access (Odoo 17+/19 raises AccessError, not
        # AttributeError, when the field exists but the model is restricted).
        wh_id = request.website.sudo().warehouse_id.id or None
    except (AttributeError, AccessError):
        pass

    if not wh_id:
        wh = request.env['stock.warehouse'].sudo().search(
            [('company_id', '=', request.env.company.id)], limit=1
        )
        wh_id = wh.id if wh else None

    return wh_id


# (código, desde%, hasta% [None = sin techo], etiqueta ES). El negocio nunca
# otorga descuentos por encima de 10%, por eso el tier superior no tiene techo
# estricto: un flat 10.0% (campaña PISA) debe caer en '5_10', no perderse por
# un borde `< 10.0`.
MD_DISCOUNT_TIERS = [
    ('0_5', 0.0, 5.0, 'Hasta 5%'),
    ('5_10', 5.0, None, 'Del 5% al 10%'),
]
_MD_DISCOUNT_TIER_BOUNDS = {code: (lo, hi) for code, lo, hi, _label in MD_DISCOUNT_TIERS}


def _selected_discount_tiers():
    valid = set(_MD_DISCOUNT_TIER_BOUNDS)
    tiers = []
    for tier in request.httprequest.args.getlist('discount_tier'):
        if tier in valid and tier not in tiers:
            tiers.append(tier)
    return tiers


def _selected_active_ingredient_ids():
    ids = []
    for ingredient_id in request.httprequest.args.getlist('active_ingredient'):
        try:
            value = int(ingredient_id)
        except (TypeError, ValueError):
            continue
        if value not in ids:
            ids.append(value)
    return ids


def _selected_product_line_ids():
    ids = []
    for line_id in request.httprequest.args.getlist('product_line'):
        try:
            value = int(line_id)
        except (TypeError, ValueError):
            continue
        if value not in ids:
            ids.append(value)
    return ids


def _lot_expiration_cutoff():
    """Cutoff datetime for lots allowed in eCommerce (today + 6 months)."""
    return fields.Datetime.now() + relativedelta(months=6)


def _warehouse_internal_location_ids(warehouse_id=None):
    """Return internal stock locations scoped to website warehouse/company."""
    if warehouse_id:
        warehouse = request.env['stock.warehouse'].sudo().browse(warehouse_id).exists()
        if warehouse:
            return request.env['stock.location'].sudo().search([
                ('usage', '=', 'internal'),
                ('company_id', '=', warehouse.company_id.id),
                ('id', 'child_of', warehouse.lot_stock_id.id),
            ]).ids

    location_domain = [
        ('usage', '=', 'internal'),
        ('company_id', '=', request.env.company.id),
    ]
    return request.env['stock.location'].sudo().search(location_domain).ids


def lot_filtered_stock_qty_map(products, warehouse_id=None):
    """Return {product_id: int_qty} using ONLY valid lots for tracked products.

    Business rule:
      - Consider only quants with lot_id.
      - Keep lots whose expiration_date is strictly greater than now + 6 months.
      - Use on-hand minus reserved per quant to mirror 'available to promise'
        behavior that the website badge already uses.
    """
    tracked = products.filtered(lambda p: p.is_storable and p.tracking in ('lot', 'serial'))
    if not tracked:
        return {}

    location_ids = _warehouse_internal_location_ids(warehouse_id)
    if not location_ids:
        return {}

    if warehouse_id:
        warehouse = request.env['stock.warehouse'].sudo().browse(warehouse_id).exists()
        company_id = warehouse.company_id.id if warehouse else request.env.company.id
    else:
        company_id = request.env.company.id

    cutoff = _lot_expiration_cutoff()
    quant_domain = [
        ('company_id', '=', company_id),
        ('product_id', 'in', tracked.ids),
        ('location_id', 'in', location_ids),
        ('lot_id', '!=', False),
        ('lot_id.expiration_date', '!=', False),
        ('lot_id.expiration_date', '>', cutoff),
        ('quantity', '>', 0),
    ]

    qty_map = defaultdict(float)
    quants = request.env['stock.quant'].sudo().search(quant_domain)
    for quant in quants:
        qty_map[quant.product_id.id] += max(0.0, quant.quantity - quant.reserved_quantity)

    return {pid: max(0, int(qty)) for pid, qty in qty_map.items()}


class ShopActiveIngredientController(WebsiteSale):

    def _active_ingredient_field_name(self):
        return request.env['product.template'].sudo()._md_active_ingredient_field_name()

    def _product_line_field_name(self):
        return request.env['product.template'].sudo()._md_product_line_field_name()

    def _relation_display_search_field(self, field_name):
        product_model = request.env['product.template'].sudo()
        relation_model = getattr(product_model._fields.get(field_name), 'comodel_name', False)
        if not relation_model or relation_model not in request.env.registry.models:
            return False

        relation_fields = request.env[relation_model].sudo()._fields
        for candidate in ('x_name', 'name', 'x_studio_name'):
            if candidate in relation_fields:
                return candidate
        return False

    def _add_search_subdomains_hook(self, search):
        extra_subdomain = super()._add_search_subdomains_hook(search)
        extra_domains = []

        ingredient_field = self._active_ingredient_field_name()
        ingredient_display_field = self._relation_display_search_field(ingredient_field)
        if ingredient_field and ingredient_display_field:
            extra_domains.append(
                Domain(f'{ingredient_field}.{ingredient_display_field}', 'ilike', search)
            )

        line_field = self._product_line_field_name()
        line_display_field = self._relation_display_search_field(line_field)
        if line_field and line_display_field:
            extra_domains.append(Domain(f'{line_field}.{line_display_field}', 'ilike', search))

        if not extra_domains:
            return extra_subdomain
        if not extra_subdomain:
            return Domain.OR(extra_domains)
        if isinstance(extra_subdomain, list):
            return Domain.OR([*extra_subdomain, *extra_domains])
        return Domain.OR([extra_subdomain, *extra_domains])

    def _md_discounted_template_ids(self, tier_codes):
        """Ids de product.template con un pricelist.item porcentual vigente
        cuyo % cae en alguno de los tiers seleccionados.

        Usa el pricelist activo del sitio (mismo mecanismo confirmado en
        docs/audits/2026-07-02_pricelist_discount_architecture.md:
        compute_price='percentage', base='list_price', date_start/date_end).
        No usa _get_combination_info por producto (caro); lee directo los
        pricelist.item vigentes, igual de preciso y sin N+1 queries.
        """
        pricelist = request.pricelist
        if not pricelist or not tier_codes:
            return []

        now = fields.Datetime.now()
        tier_domains = []
        for code in tier_codes:
            lo, hi = _MD_DISCOUNT_TIER_BOUNDS[code]
            clause = [Domain('percent_price', '>=', lo)]
            if hi is not None:
                clause.append(Domain('percent_price', '<', hi))
            tier_domains.append(Domain.AND(clause))

        domain = Domain.AND([
            Domain('pricelist_id', '=', pricelist.id),
            Domain('compute_price', '=', 'percentage'),
            Domain('base', '=', 'list_price'),
            Domain.OR([Domain('date_start', '=', False), Domain('date_start', '<=', now)]),
            Domain.OR([Domain('date_end', '=', False), Domain('date_end', '>=', now)]),
            Domain.OR(tier_domains),
        ])
        items = request.env['product.pricelist.item'].sudo().search(domain)
        tmpl_ids = set()
        for item in items:
            if item.product_tmpl_id:
                tmpl_ids.add(item.product_tmpl_id.id)
            elif item.product_id:
                tmpl_ids.add(item.product_id.product_tmpl_id.id)
        return list(tmpl_ids)

    def _get_shop_domain(self, search, category, attribute_value_dict, search_in_description=True):
        domain = super()._get_shop_domain(
            search,
            category,
            attribute_value_dict,
            search_in_description=search_in_description,
        )
        active_ingredient_ids = _selected_active_ingredient_ids()
        ingredient_field_name = self._active_ingredient_field_name()
        if ingredient_field_name and active_ingredient_ids:
            domain = Domain.AND([
                domain,
                Domain(ingredient_field_name, 'in', active_ingredient_ids),
            ])

        product_line_ids = _selected_product_line_ids()
        line_field_name = self._product_line_field_name()
        if line_field_name and product_line_ids:
            domain = Domain.AND([domain, Domain(line_field_name, 'in', product_line_ids)])

        discount_tiers = _selected_discount_tiers()
        if discount_tiers:
            domain = Domain.AND([
                domain,
                Domain('id', 'in', self._md_discounted_template_ids(discount_tiers)),
            ])
        return domain

    def _shop_get_query_url_kwargs(
        self, search, min_price, max_price, order=None, tags=None, **kwargs
    ):
        query_kwargs = super()._shop_get_query_url_kwargs(
            search, min_price, max_price, order=order, tags=tags, **kwargs
        )
        active_ingredient_ids = _selected_active_ingredient_ids()
        if active_ingredient_ids:
            query_kwargs['active_ingredient'] = active_ingredient_ids
        product_line_ids = _selected_product_line_ids()
        if product_line_ids:
            query_kwargs['product_line'] = product_line_ids

        discount_tiers = _selected_discount_tiers()
        if discount_tiers:
            query_kwargs['discount_tier'] = discount_tiers
        return query_kwargs

    def _get_additional_shop_values(self, values, **kwargs):
        values = super()._get_additional_shop_values(values, **kwargs)
        ProductTemplate = request.env['product.template'].sudo()
        active_ingredient_ids = _selected_active_ingredient_ids()
        product_line_ids = _selected_product_line_ids()
        values.update({
            'active_ingredients': ProductTemplate._md_get_shop_active_ingredients(),
            'active_ingredient_ids': active_ingredient_ids,
            'product_lines': ProductTemplate._md_get_shop_product_lines(),
            'product_line_ids': product_line_ids,
            'discount_tiers': MD_DISCOUNT_TIERS,
            'discount_tier_ids': _selected_discount_tiers(),
        })
        return values

    def _get_search_options(self, **kwargs):
        """El listado real de /shop NO usa _get_shop_domain (solo alimenta el
        rango de precio y el conteo de atributos) — usa
        product.template._search_get_detail(website, order, options), donde
        `options` es exactamente lo que retorna este método. Sin este hook,
        los filtros custom (Ingrediente Activo, Línea, Descuentos Especiales)
        nunca llegaban a filtrar el listado, solo afectaban el conteo del
        sidebar. Verificado contra el código fuente real de Odoo 19
        (addons/website_sale/controllers/main.py líneas 244-260 y
        addons/website_sale/models/product_template.py línea 864).
        """
        options = super()._get_search_options(**kwargs)

        active_ingredient_ids = _selected_active_ingredient_ids()
        ingredient_field_name = self._active_ingredient_field_name()
        if ingredient_field_name and active_ingredient_ids:
            options['md_active_ingredient_domain'] = [
                (ingredient_field_name, 'in', active_ingredient_ids)
            ]

        product_line_ids = _selected_product_line_ids()
        line_field_name = self._product_line_field_name()
        if line_field_name and product_line_ids:
            options['md_product_line_domain'] = [(line_field_name, 'in', product_line_ids)]

        discount_tiers = _selected_discount_tiers()
        if discount_tiers:
            options['md_discount_template_ids'] = self._md_discounted_template_ids(discount_tiers)

        return options


class ShopStockController(http.Controller):

    # ── Shop grid — batch cart quantities ─────────────────────────────

    @http.route(
        '/shop/cart/quantities',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def get_cart_quantities(self):
        """Return {product_id: qty} for every line in the active cart."""
        order = request.cart  # sale_get_order() removed in Odoo 19; use request.cart
        if not order:
            return {}

        quantities = {}
        for line in order.order_line:
            if line.display_type or line.is_delivery:
                continue
            pid = line.product_id.id
            quantities[pid] = quantities.get(pid, 0) + int(line.product_uom_qty)
        return quantities

    # ── Shop grid — batch stock quantities ───────────────────────────

    @http.route(
        '/shop/products/stock',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def get_products_stock(self, product_ids=None):
        """Return {str(product_id): int(free_qty)} for storable products.

        Scoped to the website's warehouse via resolve_warehouse().
        """
        if not product_ids:
            return {}

        wh_id = resolve_warehouse()
        if wh_id is None:
            return {}
        ctx = {'warehouse_id': wh_id}

        safe_ids = [int(p) for p in product_ids if p]
        products = request.env['product.product'].sudo().browse(safe_ids).exists()

        # OPTIMIZED: set warehouse context once on the entire recordset,
        # then read free_qty via search_read pattern to reduce ORM overhead.
        storable = products.filtered('is_storable').with_context(**ctx)
        lot_qty_map = lot_filtered_stock_qty_map(storable, wh_id)
        result = {}
        for product in storable:
            if product.tracking in ('lot', 'serial'):
                result[str(product.id)] = lot_qty_map.get(product.id, 0)
            else:
                result[str(product.id)] = max(0, int(product.free_qty or 0))

        return result

    # ── Product detail page — single variant stock ───────────────────

    @http.route(
        '/shop/product/availability',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def get_product_availability(self, product_id, **kwargs):
        """Return {qty, is_storable} for one product.product variant.

        Called by ProductDetailAvailability widget when the user switches
        variant on the product detail page.
        """
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            return {'qty': 0, 'is_storable': False}

        product = request.env['product.product'].sudo().browse(product_id)
        if not product.exists() or not product.is_storable:
            return {'qty': 0, 'is_storable': False}

        wh_id = resolve_warehouse()
        if wh_id is None:
            return {'qty': 0, 'is_storable': product.is_storable}
        ctx = {'warehouse_id': wh_id}
        if product.tracking in ('lot', 'serial'):
            qty = lot_filtered_stock_qty_map(product, wh_id).get(product.id, 0)
        else:
            qty = max(0, int(product.with_context(**ctx).free_qty or 0))

        return {'qty': qty, 'is_storable': True}

# NOTE: The ShopPortalController class that previously overrode
# _prepare_orders_domain has been removed. The portal orders domain
# (including sent+website_id visibility for e-commerce pre-payment orders)
# is now handled exclusively by the portal_picking_visibility module to
# avoid MRO conflicts between multiple CustomerPortal subclasses.
