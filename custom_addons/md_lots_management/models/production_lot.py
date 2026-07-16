from lxml import etree
from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class ProductionLot(models.Model):
    """
    Extensión del modelo stock.lot con personalizaciones
    que anteriormente estaban en Odoo Studio.

    Esta clase hereda del modelo nativo y agrega campos de negocio
    específicos para Medicine Depot, manteniendo compatibilidad total
    con el historial de datos.
    """

    _inherit = 'stock.lot'

    _md_tracked_fields = {
        'name': 'Número de serie/lote',
        'product_id': 'Producto',
        'ref': 'Referencia',
        'expiration_date': 'Fecha de vencimiento',
        'fecha_entrada': 'Fecha de entrada',
        'fecha_vencimiento_estimado': 'Fecha estimada',
        'estado_lote': 'Estado del lote',
        'notas_calidad': 'Notas de calidad',
        'codigo_proveedor_externo': 'Código del proveedor',
        'referencia_compra': 'Referencia de compra',
    }

    # Archivado (stock.lot nativo no lo incluye en Odoo 19)
    active = fields.Boolean(string='Activo', default=True, tracking=True)

    # Cantidad A la mano
    qty_a_la_mano = fields.Float(
        string='A la mano',
        compute='_compute_qty_a_la_mano',
        search='_search_qty_a_la_mano',
        readonly=True,
    )

    # Precio de venta público (para mostrar en consulta Handheld)
    public_sale_price = fields.Float(
        string='Precio de Venta Público',
        related='product_id.lst_price',
        digits='Product Price',
        readonly=True,
    )

    # Precio con impuestos (IVA u otros impuestos de venta del producto)
    public_sale_price_total = fields.Float(
        string='Precio de Venta con Impuestos',
        compute='_compute_public_sale_price_total',
        digits='Product Price',
    )

    has_public_sale_tax = fields.Boolean(
        string='Tiene Impuesto Adicional',
        compute='_compute_public_sale_price_total',
    )

    public_sale_price_tax_label = fields.Char(
        string='Impuesto Aplicable',
        compute='_compute_public_sale_price_total',
    )

    @api.depends('product_id.lst_price', 'product_id.taxes_id')
    def _compute_public_sale_price_total(self):
        for lot in self:
            product = lot.product_id
            taxes = product.taxes_id if product else self.env['account.tax']
            if not product or not taxes:
                lot.public_sale_price_total = product.lst_price if product else 0.0
                lot.has_public_sale_tax = False
                lot.public_sale_price_tax_label = False
                continue

            res = taxes.compute_all(product.lst_price, product=product)
            lot.public_sale_price_total = res['total_included']
            lot.has_public_sale_tax = float_compare(
                res['total_included'], product.lst_price, precision_digits=2
            ) != 0
            lot.public_sale_price_tax_label = ', '.join(taxes.mapped('name'))

    stock_por_almacen_html = fields.Html(
        string='Stock por Sucursal',
        compute='_compute_stock_por_almacen_html',
        sanitize=False,
    )

    almacenes_con_stock_ids = fields.Many2many(
        comodel_name='stock.warehouse',
        string='Sucursales con Stock',
        compute='_compute_almacenes_con_stock_ids',
        readonly=True,
    )

    ubicacion_destino_id = fields.Many2one(
        comodel_name='stock.location',
        string='Ubicación destino',
        copy=False,
        domain=[('usage', '=', 'internal')],
        groups='stock.group_stock_user',
        check_company=True,
    )

    # Campos de seguimiento y trazabilidad
    fecha_entrada = fields.Datetime(
        string='Fecha de Entrada',
        default=lambda self: fields.Datetime.now(),
        readonly=True,
        help='Fecha en que el lote ingresó al inventario',
        tracking=True,
    )

    fecha_vencimiento_estimado = fields.Date(
        string='Fecha de Vencimiento Estimado',
        help='Estimación de fecha de vencimiento (complementario a expiration_date)',
        tracking=True,
    )

    # Estado y clasificación del lote
    estado_lote = fields.Selection(
        selection=[
            ('activo', 'Activo'),
            ('pausado', 'Pausado'),
            ('agotado', 'Agotado'),
            ('descontinuado', 'Descontinuado'),
        ],
        string='Estado del Lote',
        default='activo',
        help='Estado operativo del lote',
        tracking=True,
    )

    # Notas y observaciones
    notas_calidad = fields.Text(
        string='Notas de Calidad',
        help='Observaciones sobre la calidad del lote durante inspección',
        tracking=True,
    )

    # Campos de auditoría
    usuario_creacion = fields.Many2one(
        comodel_name='res.users',
        string='Usuario que Creó',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )

    fecha_ultima_modificacion = fields.Datetime(
        string='Última Modificación',
        related='write_date',
        readonly=True,
    )

    # Campos para integraciones y referencias externas
    codigo_proveedor_externo = fields.Char(
        string='Código Externo del Proveedor',
        help='Identificador del lote asignado por el proveedor',
        tracking=True,
    )

    referencia_compra = fields.Char(
        string='Referencia de Compra',
        help='Número de orden de compra o factura asociada',
        tracking=True,
    )

    def _md_format_tracked_value(self, field_name):
        field = self._fields[field_name]
        value = self[field_name]
        if field.type == 'many2one':
            return value.display_name or ''
        if field.type == 'many2many':
            return ', '.join(value.mapped('display_name'))
        if field.type == 'selection':
            return dict(field.selection).get(value, value or '')
        if field.type == 'datetime':
            return fields.Datetime.to_string(value) if value else ''
        if field.type == 'date':
            return fields.Date.to_string(value) if value else ''
        return str(value or '')

    def _md_message_tracked_changes(self, before_values, tracked_fields):
        for lot in self:
            changes = []
            for field_name in tracked_fields:
                old_value = before_values.get(lot.id, {}).get(field_name, '')
                new_value = lot._md_format_tracked_value(field_name)
                if old_value == new_value:
                    continue
                label = self._md_tracked_fields[field_name]
                changes.append(
                    '<li><b>{}</b>: {} -&gt; {}</li>'.format(
                        escape(label),
                        escape(old_value or '-'),
                        escape(new_value or '-'),
                    )
                )
            if changes:
                lot.message_post(
                    body=Markup('<p>Histórico de cambios del lote:</p><ul>{}</ul>').format(
                        Markup(''.join(changes))
                    ),
                    subtype_xmlid='mail.mt_note',
                )

    can_manage_company = fields.Boolean(
        compute="_compute_can_manage_company",
    )

    @api.depends_context('uid')
    def _compute_can_manage_company(self):
        can = (
            self.env.user.has_group("base.group_system")
            or self.env.user.has_group("md_lots_management.group_lots_company_manager")
        )
        for rec in self:
            rec.can_manage_company = can

    def _md_normalize_lot_company_vals(self, vals):
        vals['company_id'] = False
        return vals

    def _md_normalize_company_arch(self, arch, view_type):
        can_manage = (
            self.env.user.has_group("base.group_system")
            or self.env.user.has_group("md_lots_management.group_lots_company_manager")
        )
        if view_type in ('form',):
            for node in arch.xpath("//field[@name='company_id']"):
                if can_manage:
                    node.attrib.pop('invisible', None)
                else:
                    node.set('invisible', '1')
        elif view_type in ('list', 'tree'):
            for node in arch.xpath("//field[@name='company_id']"):
                if can_manage:
                    node.attrib.pop('column_invisible', None)
                else:
                    node.set('column_invisible', '1')
        elif view_type == 'search':
            for node in arch.xpath('//filter'):
                name = node.get('name') or ''
                context = node.get('context') or ''
                if name in ('group_by_Company', 'group_by_company') or 'company_id' in context:
                    if not can_manage:
                        node.set('groups', 'base.group_system')

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        if view_type in ('form', 'list', 'tree', 'search'):
            self._md_normalize_company_arch(arch, view_type)
        return arch, view

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'company_id' in fields_list:
            defaults['company_id'] = False
        return defaults

    @staticmethod
    def _md_lot_key(vals):
        name = (vals.get('name') or '').strip()
        product_id = vals.get('product_id')
        if hasattr(product_id, 'id'):
            product_id = product_id.id
        elif isinstance(product_id, (list, tuple)):
            product_id = product_id[0] if product_id else False
        company_id = vals.get('company_id') or False
        if not name or not product_id:
            return False
        return (name, product_id, company_id)

    def _md_find_existing_lot(self, name, product_id, company_id):
        base_domain = [
            ('name', '=', name),
            ('product_id', '=', product_id),
        ]
        lot_model = self.sudo().with_context(active_test=False)
        lot = lot_model.search(base_domain + [('company_id', '=', company_id)], limit=1)
        if lot:
            return lot

        lot = lot_model.search(base_domain + [('company_id', '!=', False)], limit=1)
        if lot:
            lot.write({'company_id': False})
            return lot

        return lot

    def _get_qty_a_la_mano_locations(self):
        location_domain = [
            ('usage', '=', 'internal'),
            ('company_id', 'in', list(self.env.companies.ids) + [False]),
        ]

        warehouse_id = (
            self.env.context.get('warehouse_id')
            or self.env.context.get('default_warehouse_id')
        )
        location_id = (
            self.env.context.get('location_id')
            or self.env.context.get('default_location_id')
        )

        if location_id:
            location_domain.insert(0, ('id', 'child_of', location_id))
        elif warehouse_id:
            warehouse = self.env['stock.warehouse'].browse(warehouse_id).exists()
            if warehouse and warehouse.lot_stock_id:
                location_domain.insert(0, ('id', 'child_of', warehouse.lot_stock_id.id))

        return self.env['stock.location'].search(location_domain)

    def _get_qty_a_la_mano_quant_domain(self, lot_ids=None):
        location_ids = self._get_qty_a_la_mano_locations().ids
        domain = [
            ('company_id', 'in', self.env.companies.ids),
            ('location_id', 'in', location_ids),
            ('lot_id', '!=', False),
        ]
        if lot_ids:
            domain.append(('lot_id', 'in', lot_ids))
        return domain

    @staticmethod
    def _qty_a_la_mano_matches(qty, operator, value):
        value = float(value or 0.0)
        if operator in ('=', '=='):
            return qty == value
        if operator == '!=':
            return qty != value
        if operator == '>':
            return qty > value
        if operator == '>=':
            return qty >= value
        if operator == '<':
            return qty < value
        if operator == '<=':
            return qty <= value
        return False

    @api.depends('quant_ids.quantity', 'quant_ids.location_id', 'quant_ids.company_id')
    @api.depends_context('company', 'warehouse_id', 'location_id')
    def _compute_qty_a_la_mano(self):
        qty_by_lot = dict.fromkeys(self.ids, 0.0)
        if self.ids:
            quant_groups = self.env['stock.quant']._read_group(
                self._get_qty_a_la_mano_quant_domain(self.ids),
                ['lot_id'],
                ['quantity:sum'],
            )
            qty_by_lot.update({
                lot.id: quantity_sum or 0.0
                for lot, quantity_sum in quant_groups
                if lot
            })

        for lot in self:
            qty = qty_by_lot.get(lot.id, 0.0)
            lot.qty_a_la_mano = qty

    def _search_qty_a_la_mano(self, operator, value):
        if operator == '=?':
            operator = '='
        if operator not in ('=', '==', '!=', '>', '>=', '<', '<='):
            return [('id', '=', 0)]

        quant_groups = self.env['stock.quant']._read_group(
            self._get_qty_a_la_mano_quant_domain(),
            ['lot_id'],
            ['quantity:sum'],
        )
        grouped_lot_ids = []
        matching_lot_ids = []
        for lot, quantity_sum in quant_groups:
            if not lot:
                continue
            lot_id = lot.id
            qty = quantity_sum or 0.0
            grouped_lot_ids.append(lot_id)
            if self._qty_a_la_mano_matches(qty, operator, value):
                matching_lot_ids.append(lot_id)

        if self._qty_a_la_mano_matches(0.0, operator, value):
            if matching_lot_ids:
                return [
                    '|',
                    ('id', 'in', matching_lot_ids),
                    ('id', 'not in', grouped_lot_ids),
                ]
            return [('id', 'not in', grouped_lot_ids)]
        return [('id', 'in', matching_lot_ids)]

    @api.depends('quant_ids.quantity', 'quant_ids.reserved_quantity', 'quant_ids.location_id')
    @api.depends_context('company')
    def _compute_stock_por_almacen_html(self):
        warehouses = self.env['stock.warehouse'].search(
            [('company_id', 'in', self.env.companies.ids)],
            order='name',
        )

        for lot in self:
            if not lot.id:
                lot.stock_por_almacen_html = False
                continue

            quants = self.env['stock.quant'].search([
                ('lot_id', '=', lot.id),
                ('location_id.usage', '=', 'internal'),
            ])

            rows = []
            total_qty = total_reserved = 0.0

            for wh in warehouses:
                child_ids = self.env['stock.location'].search([
                    ('id', 'child_of', wh.lot_stock_id.id),
                    ('usage', '=', 'internal'),
                ]).ids
                wh_quants = quants.filtered(lambda q: q.location_id.id in child_ids)
                qty = sum(wh_quants.mapped('quantity'))
                reserved = sum(wh_quants.mapped('reserved_quantity'))
                disponible = qty - reserved
                total_qty += qty
                total_reserved += reserved
                rows.append((wh.name, qty, reserved, disponible))

            if not any(qty for _, qty, _, _ in rows):
                lot.stock_por_almacen_html = Markup(
                    '<p class="text-muted fst-italic ms-1 mt-2">'
                    'Sin stock en almacenes internos.'
                    '</p>'
                )
                continue

            tbody = Markup('').join(
                Markup(
                    '<tr>'
                    '<td>{name}</td>'
                    '<td class="text-end">{qty}</td>'
                    '<td class="text-end text-muted">{reserved}</td>'
                    '<td class="text-end fw-semibold {cls}">{disp}</td>'
                    '</tr>'
                ).format(
                    name=escape(name),
                    qty='{:,.2f}'.format(qty),
                    reserved='{:,.2f}'.format(reserved),
                    disp='{:,.2f}'.format(disp),
                    cls='text-success' if disp > 0 else ('text-danger' if disp < 0 else 'text-muted'),
                )
                for name, qty, reserved, disp in rows
            )

            total_disp = total_qty - total_reserved
            lot.stock_por_almacen_html = Markup(
                '<table class="table table-sm table-bordered mb-0">'
                '<thead class="table-light">'
                '<tr>'
                '<th>Almacén / Sucursal</th>'
                '<th class="text-end">A la Mano</th>'
                '<th class="text-end">Reservado</th>'
                '<th class="text-end">Disponible</th>'
                '</tr>'
                '</thead>'
                '<tbody>{tbody}</tbody>'
                '<tfoot class="fw-bold table-secondary">'
                '<tr>'
                '<td>Total</td>'
                '<td class="text-end">{total_qty}</td>'
                '<td class="text-end">{total_reserved}</td>'
                '<td class="text-end">{total_disp}</td>'
                '</tr>'
                '</tfoot>'
                '</table>'
            ).format(
                tbody=tbody,
                total_qty='{:,.2f}'.format(total_qty),
                total_reserved='{:,.2f}'.format(total_reserved),
                total_disp='{:,.2f}'.format(total_disp),
            )

    @api.depends('quant_ids.quantity', 'quant_ids.location_id')
    @api.depends_context('company')
    def _compute_almacenes_con_stock_ids(self):
        lot_wh_map = {lot.id: self.env['stock.warehouse'].browse() for lot in self}
        warehouses = self.env['stock.warehouse'].search(
            [('company_id', 'in', self.env.companies.ids)],
            order='name',
        )
        if self.ids and warehouses:
            for wh in warehouses:
                wh_loc_ids = self.env['stock.location'].search([
                    ('id', 'child_of', wh.lot_stock_id.id),
                    ('usage', '=', 'internal'),
                ]).ids
                if not wh_loc_ids:
                    continue
                quant_groups = self.env['stock.quant']._read_group(
                    domain=[
                        ('lot_id', 'in', self.ids),
                        ('location_id', 'in', wh_loc_ids),
                        ('quantity', '>', 0),
                    ],
                    groupby=['lot_id'],
                    aggregates=['quantity:sum'],
                )
                for lot, qty_sum in quant_groups:
                    if lot and lot.id in lot_wh_map and (qty_sum or 0) > 0:
                        lot_wh_map[lot.id] |= wh
        for lot in self:
            lot.almacenes_con_stock_ids = lot_wh_map.get(
                lot.id, self.env['stock.warehouse'].browse()
            )

    def _md_prepare_a_la_mano_values(self, vals):
        cantidad_ingresada = vals.pop('cantidad_entrada_a_la_mano', False)
        ubicacion_destino_id = vals.pop('ubicacion_destino_id', False)

        if cantidad_ingresada in (False, None, ''):
            cantidad_ingresada = (
                self.env.context.get('cantidad_entrada_a_la_mano')
                or self.env.context.get('default_cantidad_entrada_a_la_mano')
            )

        if not cantidad_ingresada:
            return {}

        if not ubicacion_destino_id:
            ubicacion_destino_id = (
                self.env.context.get('ubicacion_destino_id')
                or self.env.context.get('default_ubicacion_destino_id')
                or self.env.context.get('location_id')
                or self.env.context.get('default_location_id')
            )

        if not ubicacion_destino_id:
            raise ValidationError(
                'Selecciona una ubicación destino para actualizar la cantidad A la mano.'
            )

        return {
            'cantidad_ingresada': cantidad_ingresada,
            'ubicacion_destino': ubicacion_destino_id,
        }

    def _md_apply_a_la_mano_quantity(self, cantidad_ingresada, ubicacion_destino):
        self.ensure_one()
        cantidad_ingresada = float(cantidad_ingresada or 0.0)
        if cantidad_ingresada <= 0:
            raise ValidationError('La cantidad A la mano debe ser mayor que cero.')

        ubicacion_destino = self.env['stock.location'].browse(
            getattr(ubicacion_destino, 'id', ubicacion_destino)
        ).exists()
        if not ubicacion_destino:
            raise ValidationError(
                'Selecciona una ubicación destino para actualizar la cantidad A la mano.'
            )
        if ubicacion_destino.usage != 'internal':
            raise ValidationError(
                'La ubicación destino debe ser interna para actualizar la cantidad A la mano.'
            )

        lote = self
        quant_model = self.env['stock.quant'].sudo().with_context(inventory_mode=True)
        quant = quant_model.search([
            ('product_id', '=', lote.product_id.id),
            ('lot_id', '=', lote.id),
            ('location_id', '=', ubicacion_destino.id),
            ('package_id', '=', False),
            ('owner_id', '=', False),
        ], limit=1)

        if not quant:
            quant = quant_model.create({
                'product_id': lote.product_id.id,
                'lot_id': lote.id,
                'location_id': ubicacion_destino.id,
            })

        quant.inventory_quantity = quant.quantity + cantidad_ingresada
        quant.action_apply_inventory()
        lote.invalidate_recordset(['qty_a_la_mano'])
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'A la mano',
                'message': (
                    'La cantidad A la mano ha sido actualizada correctamente '
                    'para el lote {}'.format(lote.name)
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Patrón get-or-create: si el lote ya existe para (name, product_id, company_id),
        retorna el registro existente en lugar de intentar duplicarlo.
        La cantidad A la mano por sucursal se gestiona por ubicación receptora,
        no creando un lote nuevo por cada ubicación.
        Odoo conserva su trazabilidad nativa porque las líneas de movimiento reciben el
        mismo recordset stock.lot esperado; solo se evita insertar una clave duplicada.
        """
        lots_by_position = [self.browse()] * len(vals_list)
        to_create = []
        to_create_metadata = []
        existing_a_la_mano_values = []
        pending_by_key = {}

        for position, vals in enumerate(vals_list):
            vals = dict(vals)
            a_la_mano_values = self._md_prepare_a_la_mano_values(vals)
            if 'usuario_creacion' not in vals:
                vals['usuario_creacion'] = self.env.user.id

            name = (vals.get('name') or '').strip()
            if name:
                vals['name'] = name
            product_id = vals.get('product_id')
            if hasattr(product_id, 'id'):
                product_id = product_id.id
            elif isinstance(product_id, (list, tuple)):
                product_id = product_id[0] if product_id else False
            self._md_normalize_lot_company_vals(vals)
            company_id = vals.get('company_id') or False
            lot_key = self._md_lot_key(vals)

            if name and product_id:
                lot = self._md_find_existing_lot(name, product_id, company_id)
                if lot:
                    lots_by_position[position] = self.browse(lot.id)
                    if a_la_mano_values:
                        existing_a_la_mano_values.append((
                            self.browse(lot.id),
                            a_la_mano_values,
                        ))
                    continue

            if lot_key and lot_key in pending_by_key:
                to_create_metadata[pending_by_key[lot_key]]['positions'].append(position)
                if a_la_mano_values:
                    to_create_metadata[pending_by_key[lot_key]]['a_la_mano_values'].append(
                        a_la_mano_values
                    )
                continue

            if lot_key:
                pending_by_key[lot_key] = len(to_create)
            to_create.append(vals)
            to_create_metadata.append({
                'positions': [position],
                'a_la_mano_values': [a_la_mano_values] if a_la_mano_values else [],
            })

        new_lots = super().create(to_create) if to_create else self.browse()

        for lot, metadata in zip(new_lots, to_create_metadata):
            for position in metadata['positions']:
                lots_by_position[position] = lot
            for a_la_mano_values in metadata['a_la_mano_values']:
                lot._md_apply_a_la_mano_quantity(**a_la_mano_values)

        for lot, a_la_mano_values in existing_a_la_mano_values:
            lot._md_apply_a_la_mano_quantity(**a_la_mano_values)

        lots = self.browse()
        for lot in lots_by_position:
            lots += lot
        return lots

    def write(self, vals):
        """Actualiza campos auditables al modificar el lote."""
        vals = dict(vals)
        # md_assign_company=True permite que admins asignen empresa explícitamente
        # sin que la normalización global lo revierta a False.
        can_manage = self.env.user.has_group("md_lots_management.group_lots_company_manager")
        if ('product_id' in vals or 'company_id' in vals) and not self.env.context.get('md_assign_company') and not can_manage:
            self._md_normalize_lot_company_vals(vals)

        tracked_fields = [
            field_name
            for field_name in vals
            if field_name in self._md_tracked_fields
        ]
        before_values = {
            lot.id: {
                field_name: lot._md_format_tracked_value(field_name)
                for field_name in tracked_fields
            }
            for lot in self
        }
        result = super().write(vals)
        if tracked_fields:
            self._md_message_tracked_changes(before_values, tracked_fields)
        return result

    @api.constrains('fecha_vencimiento_estimado', 'expiration_date')
    def _check_expiration_dates(self):
        """Valida que las fechas de vencimiento tengan sentido."""
        for lot in self:
            if (lot.fecha_vencimiento_estimado
                    and lot.expiration_date
                    and lot.fecha_vencimiento_estimado > lot.expiration_date):
                raise ValidationError(
                    'La fecha de vencimiento estimado no puede ser posterior '
                    'a la fecha de vencimiento oficial.'
                )

    def action_lot_open_quants(self):
        """Abre la lista de quants filtrada por este lote."""
        self.ensure_one()
        domain = self._get_qty_a_la_mano_quant_domain([self.id])
        domain.append(('quantity', '!=', 0))
        return {
            'type': 'ir.actions.act_window',
            'name': 'A la mano',
            'res_model': 'stock.quant',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'search_default_lot_id': self.id},
        }

    def action_open_quants(self):
        return self.action_lot_open_quants()

    def action_open_a_la_mano_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'A la mano',
            'res_model': 'md.lot.a.la.mano.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lot_id': self.id,
                'default_ubicacion_destino_id': self.env.context.get('location_id')
                or self.env.context.get('default_location_id'),
            },
        }

    def action_assign_company(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Asignar Empresa',
            'res_model': 'md.lot.assign.company.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lot_id': self.id,
                'default_company_id': self.company_id.id if self.company_id else False,
            },
        }

    def unlink(self):
        # Archivar en lugar de eliminar para evitar FK violations con stock.quant.
        self.write({'active': False})
        return True

    def action_clean_archived_company(self):
        lots = self.env['stock.lot'].sudo().with_context(active_test=False).search([
            ('active', '=', False),
            ('company_id', '!=', False),
        ])
        count_ok = 0
        count_skip = 0
        for lot in lots:
            try:
                with self.env.cr.savepoint():
                    lot.write({'company_id': False})
                count_ok += 1
            except Exception:
                count_skip += 1
        if count_ok or count_skip:
            msg = 'Se limpiaron %d lote(s) archivado(s).' % count_ok
            if count_skip:
                msg += ' %d omitido(s) por conflicto de unicidad (mismo producto+número en varias empresas).' % count_skip
            msg_type = 'success' if count_ok else 'warning'
        else:
            msg = 'No se encontraron lotes archivados con empresa asignada.'
            msg_type = 'warning'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Empresa removida',
                'message': msg,
                'type': msg_type,
                'sticky': True,
            },
        }
