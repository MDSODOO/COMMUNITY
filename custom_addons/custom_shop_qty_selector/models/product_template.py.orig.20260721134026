from collections import defaultdict

from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_encode

from odoo import api, fields, models, tools


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _description = 'Product Template (MD shop qty/ingredient extensions)'

    show_qty_a_la_mano = fields.Boolean(
        string='Mostrar A la mano',
        compute='_compute_qty_a_la_mano',
        compute_sudo=True,
        help='Activa la señal A la mano en website para productos almacenables.',
    )
    qty_a_la_mano = fields.Float(
        string='A la mano',
        compute='_compute_qty_a_la_mano',
        compute_sudo=True,
        digits='Product Unit of Measure',
        help='Cantidad A la mano calculada para el almacén del website.',
    )

    @api.depends(
        'product_variant_ids',
        'product_variant_ids.free_qty',
        'product_variant_ids.is_storable',
        'product_variant_ids.tracking',
    )
    @api.depends_context('warehouse_id', 'website_id', 'company')
    def _compute_qty_a_la_mano(self):
        website = self._md_current_website()
        warehouse = self._md_current_warehouse(website)
        qty_context = {'warehouse_id': warehouse.id} if warehouse else {}

        for template in self:
            variants = template.sudo().product_variant_ids.filtered('is_storable')
            qty = sum(
                template._md_variant_qty_a_la_mano(variant, website, qty_context)
                for variant in variants
            )
            template.qty_a_la_mano = max(0.0, qty)
            template.show_qty_a_la_mano = bool(variants)

    @api.model
    def _md_current_website(self):
        Website = self.env['website'].sudo()
        website_id = self.env.context.get('website_id')
        if website_id:
            website = Website.browse(website_id).exists()
            if website:
                return website[:1]

        try:
            return Website.get_current_website().sudo()[:1]
        except Exception:  # noqa: BLE001 - safe fallback for non-HTTP ORM calls.
            return Website.browse()

    @api.model
    def _md_current_warehouse(self, website=None):
        Warehouse = self.env['stock.warehouse'].sudo()
        warehouse_id = self.env.context.get('warehouse_id')
        if warehouse_id:
            warehouse = Warehouse.browse(warehouse_id).exists()
            if warehouse:
                return warehouse[:1]

        if (
            website
            and website.exists()
            and 'warehouse_id' in website._fields
            and website.warehouse_id
        ):
            return website.warehouse_id.sudo()

        return Warehouse.search([('company_id', '=', self.env.company.id)], limit=1)

    @api.model
    def _md_variant_qty_a_la_mano(self, variant, website=None, qty_context=None):
        variant = variant.sudo().exists()
        if not variant or not variant.is_storable:
            return 0.0

        if (
            variant.tracking in ('lot', 'serial')
            and website
            and hasattr(website, '_md_lot_filtered_available_qty')
        ):
            return website._md_lot_filtered_available_qty(variant)

        return variant.with_context(**(qty_context or {})).free_qty or 0.0

    @api.model
    def _md_get_sales_popularity(self, products, days=90):
        """{product.template.id: unidades vendidas} en pos.order.line +
        sale.order.line de los últimos `days` días, para `products`.

        Usado para ordenar los filtros de Ingrediente Activo / Línea por
        popularidad real en vez de alfabético. Se combinan POS y ventas en
        línea (no solo sale.order) porque la mayoría de las ventas de esta
        farmacia ocurren en mostrador, no en el sitio web — ordenar solo por
        ventas en línea daría un ranking que no refleja la demanda real.

        No se filtra por company_id a propósito: sudo() ya bypassa las
        reglas multi-compañía, y cada sucursal es una res.company distinta
        (ver docs/audits/2026-07-02_pricelist_discount_architecture.md) —
        queremos la popularidad agregada de las 6 sucursales, no solo la
        compañía dueña del sitio web.
        """
        if not products:
            return {}

        cutoff = fields.Datetime.now() - relativedelta(days=days)
        variant_to_tmpl = {
            variant.id: product.id
            for product in products
            for variant in product.sudo().product_variant_ids
        }
        if not variant_to_tmpl:
            return {}

        variant_ids = list(variant_to_tmpl.keys())
        qty_by_tmpl = defaultdict(float)

        sale_groups = self.env['sale.order.line'].sudo()._read_group(
            domain=[
                ('product_id', 'in', variant_ids),
                ('order_id.state', 'in', ('sale', 'done')),
                ('order_id.date_order', '>=', cutoff),
            ],
            groupby=['product_id'],
            aggregates=['product_uom_qty:sum'],
        )
        for product, qty in sale_groups:
            qty_by_tmpl[variant_to_tmpl[product.id]] += qty or 0.0

        pos_groups = self.env['pos.order.line'].sudo()._read_group(
            domain=[
                ('product_id', 'in', variant_ids),
                ('order_id.state', 'in', ('paid', 'done', 'invoiced')),
                ('order_id.date_order', '>=', cutoff),
            ],
            groupby=['product_id'],
            aggregates=['qty:sum'],
        )
        for product, qty in pos_groups:
            qty_by_tmpl[variant_to_tmpl[product.id]] += qty or 0.0

        return qty_by_tmpl

    @api.model
    def _md_get_relation_popularity_score(self, products, field_name):
        """{related_record.id: unidades vendidas} agregando la venta de cada
        producto sobre todos los valores de `field_name` que tenga (m2o o
        m2m indistintamente)."""
        qty_by_tmpl = self._md_get_sales_popularity(products)
        score = defaultdict(float)
        for product in products:
            qty = qty_by_tmpl.get(product.id, 0.0)
            if not qty:
                continue
            for related in product.sudo()[field_name]:
                score[related.id] += qty
        return score

    @api.model
    def _md_relation_display_name(self, record):
        if not record:
            return ''
        for field_name in ('x_name', 'name', 'x_studio_name'):
            if field_name in record._fields and record[field_name]:
                return record[field_name]
        return record.display_name or ''

    @api.model
    @tools.ormcache()
    def _md_active_ingredient_field_name(self):
        """Return the field name linking products to their active ingredient/substance.

        Acepta tanto el modelo de Studio original (x_active_ingredient) como
        nuestro modelo propio (md.active.substance, ver md_pharma_regulatory),
        para que funcione en instancias que no usen Studio.
        """
        field_candidates = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'product.template'),
            ('relation', 'in', ('x_active_ingredient', 'md.active.substance')),
            ('ttype', 'in', ('many2one', 'many2many')),
        ])
        if not field_candidates:
            return False

        def _score(field):
            name = (field.name or '').lower()
            label = (field.field_description or '').lower()
            text = f'{name} {label}'
            return (
                0 if 'ingred' in text else 1,
                0 if 'active' in text or 'activo' in text else 1,
                field.id,
            )

        return field_candidates.sorted(_score)[:1].name

    def _md_get_active_ingredients(self):
        field_name = self._md_active_ingredient_field_name()
        relation_model = getattr(self._fields.get(field_name), 'comodel_name', False)
        if not field_name or not relation_model:
            return self.env[relation_model].browse() if relation_model else self.browse()[0:0]

        return self.sudo().mapped(field_name).sudo().exists()

    @api.model
    def _md_active_ingredient_name(self, ingredient):
        return self._md_relation_display_name(ingredient)

    @api.model
    def _md_active_ingredient_shop_url(self, ingredient):
        ingredient_name = self._md_active_ingredient_name(ingredient)
        query = url_encode({
            'search': ingredient_name,
            'active_ingredient': ingredient.id,
        })
        return f'/shop?{query}'

    @api.model
    def _md_get_shop_active_ingredients(self):
        field_name = self._md_active_ingredient_field_name()
        relation_model = getattr(self._fields.get(field_name), 'comodel_name', False) if field_name else False
        if not field_name or not relation_model:
            return self.env[relation_model].browse() if relation_model else self.browse()[0:0]

        products = self.sudo().search(self.env['website'].get_current_website().sale_product_domain())
        ingredients = products.mapped(field_name).sudo().exists()

        # Orden por popularidad de venta (POS + en línea, últimos 90 días,
        # ver _md_get_sales_popularity), no alfabético. Empate/sin ventas
        # cae a alfabético como desempate estable.
        score = self._md_get_relation_popularity_score(products, field_name)
        return ingredients.sorted(
            key=lambda ingredient: (-score.get(ingredient.id, 0.0), self._md_active_ingredient_name(ingredient).lower())
        )

    @api.model
    @tools.ormcache()
    def _md_product_line_field_name(self):
        """Return the Studio field name linking products to x_line."""
        field_candidates = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'product.template'),
            ('relation', '=', 'x_line'),
            ('ttype', 'in', ('many2one', 'many2many')),
        ])
        if not field_candidates:
            return False

        def _score(field):
            name = (field.name or '').lower()
            label = (field.field_description or '').lower()
            text = f'{name} {label}'
            return (
                0 if 'line' in text or 'línea' in text or 'linea' in text else 1,
                0 if 'studio' not in name else 1,
                field.id,
            )

        return field_candidates.sorted(_score)[:1].name

    def _md_get_product_lines(self):
        field_name = self._md_product_line_field_name()
        relation_model = getattr(self._fields.get(field_name), 'comodel_name', False)
        if not field_name or not relation_model:
            return self.env[relation_model].browse() if relation_model else self.browse()[0:0]

        return self.sudo().mapped(field_name).sudo().exists()

    @api.model
    def _md_product_line_name(self, line):
        return self._md_relation_display_name(line)

    @api.model
    def _md_product_line_shop_url(self, line):
        line_name = self._md_product_line_name(line)
        query = url_encode({
            'search': line_name,
            'product_line': line.id,
        })
        return f'/shop?{query}'

    @api.model
    def _md_get_shop_product_lines(self):
        field_name = self._md_product_line_field_name()
        relation_model = getattr(self._fields.get(field_name), 'comodel_name', False) if field_name else False
        if not field_name or not relation_model:
            return self.env[relation_model].browse() if relation_model else self.browse()[0:0]

        products = self.sudo().search(self.env['website'].get_current_website().sale_product_domain())
        lines = products.mapped(field_name).sudo().exists()

        # Orden por popularidad de venta (POS + en línea, últimos 90 días,
        # ver _md_get_sales_popularity), no alfabético. Empate/sin ventas
        # cae a alfabético como desempate estable.
        score = self._md_get_relation_popularity_score(products, field_name)
        return lines.sorted(
            key=lambda line: (-score.get(line.id, 0.0), self._md_product_line_name(line).lower())
        )

    def _search_get_detail(self, website, order, options):
        """El listado de /shop se arma acá (vía website._search_with_fuzzy),
        NO en WebsiteSale._get_shop_domain (ese solo alimenta el rango de
        precio y el conteo de atributos del sidebar — verificado contra el
        código fuente real de Odoo 19). `options` es lo que retorna
        ShopActiveIngredientController._get_search_options en
        custom_shop_qty_selector/controllers/main.py; ahí se resuelven los 3
        filtros custom (Ingrediente Activo, Línea, Descuentos Especiales) a
        fragmentos de dominio simples para no requerir `request` acá.
        """
        result = super()._search_get_detail(website, order, options)

        ingredient_domain = options.get('md_active_ingredient_domain')
        if ingredient_domain:
            result['base_domain'].append(ingredient_domain)

        line_domain = options.get('md_product_line_domain')
        if line_domain:
            result['base_domain'].append(line_domain)

        discount_template_ids = options.get('md_discount_template_ids')
        if discount_template_ids is not None:
            result['base_domain'].append([('id', 'in', discount_template_ids)])

        return result
