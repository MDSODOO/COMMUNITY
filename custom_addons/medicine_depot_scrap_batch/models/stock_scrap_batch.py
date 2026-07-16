from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class StockScrapBatch(models.Model):
    _name = 'stock.scrap.batch'
    _description = 'Orden de bajas múltiple'
    _order = 'id desc'

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        default='New',
    )
    date = fields.Datetime(
        string='Fecha',
        default=fields.Datetime.now,
        required=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('waiting', 'En Validación'),
            ('done', 'Validado'),
        ],
        string='Estado',
        default='draft',
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True,
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Ubicación Origen',
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        required=True,
    )
    scrap_location_id = fields.Many2one(
        'stock.location',
        string='Ubicación de bajas',
        default=lambda self: self._default_scrap_location(),
        domain=lambda self: self._get_scrap_location_domain(),
        required=True,
    )
    line_ids = fields.One2many(
        'stock.scrap.batch.line',
        'batch_id',
        string='Líneas',
        copy=True,
    )
    scrap_count = fields.Integer(
        string='Bajas generadas',
        compute='_compute_scrap_count',
    )
    scrap_history_ids = fields.Many2many(
        'stock.scrap',
        string='Historial de secuencias',
        compute='_compute_scrap_history_ids',
        compute_sudo=True,
        readonly=True,
    )
    scrap_reason_tag_ids = fields.Many2many(
        'stock.scrap.reason.tag',
        string='Motivo de la baja',
        compute='_compute_scrap_reason_tag_ids',
        inverse='_inverse_scrap_reason_tag_ids',
        readonly=False,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    line_count = fields.Integer(
        string='Total de Líneas',
        compute='_compute_line_count',
        store=True,
    )
    total_cost = fields.Monetary(
        string='Costo total',
        compute='_compute_total_cost',
        currency_field='currency_id',
    )

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends('line_ids.scrap_total_cost')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = sum(rec.line_ids.mapped('scrap_total_cost'))

    @api.depends('line_ids.scrap_id')
    def _compute_scrap_count(self):
        for rec in self:
            rec.scrap_count = len(rec.line_ids.filtered('scrap_id'))

    @api.depends('company_id')
    def _compute_scrap_history_ids(self):
        Scrap = self.env['stock.scrap']
        for rec in self:
            if rec.company_id:
                rec.scrap_history_ids = Scrap.search([
                    ('company_id', '=', rec.company_id.id),
                    ('state', '=', 'done'),
                ], order='date_done desc, name desc, id desc')
            else:
                rec.scrap_history_ids = False

    @api.depends('line_ids.scrap_reason_tag_ids')
    def _compute_scrap_reason_tag_ids(self):
        for rec in self:
            rec.scrap_reason_tag_ids = rec.line_ids.mapped('scrap_reason_tag_ids')

    def _inverse_scrap_reason_tag_ids(self):
        for rec in self:
            if rec.line_ids:
                rec.line_ids.write({
                    'scrap_reason_tag_ids': [Command.set(rec.scrap_reason_tag_ids.ids)],
                })

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('stock.scrap.batch') or 'New'
            self._enforce_scrap_location(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._enforce_scrap_location(vals)
        return super().write(vals)

    @api.model
    def _resolve_scrap_location(self):
        """Localiza Virtual Locations/Scrap con cuatro niveles de fallback
        para garantizar compatibilidad con Odoo 17/18/19 y entornos donde
        el XMLID no está en ir.model.data.

        1. XML ID estándar de Odoo (más preciso)
        2. Campo booleano scrap_location / is_scrap_location
        3. Nombre corto exacto 'Scrap' con usage='inventory'
        4. Búsqueda parcial por nombre (última defensa)
        """
        company_domain = [
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.env.company.id),
        ]
        # Nivel 1 — XMLID
        loc = self.env.ref('stock.stock_location_scrapped', raise_if_not_found=False)
        if loc:
            return loc
        # Nivel 2 — campo booleano (varía entre versiones de Odoo)
        loc_fields = self.env['stock.location']._fields
        for field_name in ('is_scrap_location', 'scrap_location'):
            if field_name in loc_fields:
                loc = self.env['stock.location'].search(
                    [(field_name, '=', True)] + company_domain, limit=1
                )
                if loc:
                    return loc
        # Nivel 3 — nombre exacto 'Scrap' con usage virtual (evita coincidir con Inventory Adjustment)
        loc = self.env['stock.location'].search(
            [('name', '=', 'Scrap'), ('usage', '=', 'inventory')] + company_domain,
            limit=1,
        )
        if loc:
            return loc
        # Nivel 4 — búsqueda parcial como última defensa
        return self.env['stock.location'].search(
            [('name', 'ilike', 'Scrap'), ('usage', '=', 'inventory')] + company_domain,
            limit=1,
        )

    @api.model
    def _default_scrap_location(self):
        return self._resolve_scrap_location().id or False

    @api.model
    def _get_default_scrap_location(self):
        return self._resolve_scrap_location()

    @api.model
    def _enforce_scrap_location(self, vals):
        """Ancla siempre la ubicación de bajas a Virtual Locations/Scrap,
        sin excepción por rol, para prevenir errores operativos críticos."""
        default_location = self._get_default_scrap_location()
        if default_location:
            vals['scrap_location_id'] = default_location.id

    @api.model
    def _get_scrap_location_domain(self):
        """Compatibilidad entre versiones de Odoo:
        - Algunas usan stock.location.is_scrap_location
        - Otras usan stock.location.scrap_location
        - En otras, las ubicaciones de desecho se distinguen por usage='inventory'
        """
        location_fields = self.env['stock.location']._fields
        if 'is_scrap_location' in location_fields:
            domain = [('is_scrap_location', '=', True)]
        elif 'scrap_location' in location_fields:
            domain = [('scrap_location', '=', True)]
        else:
            domain = [('usage', '=', 'inventory')]
        domain.extend([
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.env.company.id),
        ])
        return domain

    def action_request_validation(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_('Agrega al menos una línea antes de solicitar validación.'))
            if not rec.scrap_location_id:
                rec.scrap_location_id = rec._get_default_scrap_location()
            rec.state = 'waiting'

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_validate_batch(self):
        if not self.env.user.has_group('stock.group_stock_manager'):
                raise UserError(_('Solo un Administrador de Inventario puede validar esta orden.'))

        for rec in self:
            if rec.state != 'waiting':
                continue
            if not rec.line_ids:
                raise UserError(_('No hay líneas para validar en la orden %s.') % rec.display_name)

            for line in rec.line_ids:
                line._validate_line_data()
                vals = {
                    'product_id': line.product_id.id,
                    'scrap_qty': line.scrap_qty,
                    'product_uom_id': line.product_uom_id.id,
                    'lot_id': line.lot_id.id or False,
                    'location_id': line.location_id.id,
                    'scrap_location_id': line.scrap_location_id.id,
                    'company_id': rec.company_id.id,
                    'origin': rec.name,
                }
                if line.scrap_reason_tag_ids:
                    vals['scrap_reason_tag_ids'] = [Command.set(line.scrap_reason_tag_ids.ids)]
                scrap = self.env['stock.scrap'].create(vals)
                scrap.action_validate()
                line.scrap_id = scrap

            rec.state = 'done'

    def action_view_scraps(self):
        self.ensure_one()
        scraps = self.line_ids.mapped('scrap_id')
        action = self.env.ref('stock.action_stock_scrap').sudo().read()[0]
        action['domain'] = [('id', 'in', scraps.ids)]
        if len(scraps) == 1:
            form_view = self.env['ir.ui.view'].search(
                [('model', '=', 'stock.scrap'), ('type', '=', 'form')], limit=1
            )
            if form_view:
                action['views'] = [(form_view.id, 'form')]
            action['res_id'] = scraps.id
        return action

    def action_view_scrap_history(self):
        self.ensure_one()
        action = self.env.ref('stock.action_stock_scrap').sudo().read()[0]
        action['domain'] = [('id', 'in', self.scrap_history_ids.ids)]
        return action

    def action_view_legacy_history(self):
        self.ensure_one()
        action = self.env.ref(
            'medicine_depot_scrap_batch.action_medicine_depot_scrap_history_legacy'
        ).sudo().read()[0]
        action['domain'] = [('company_id', '=', self.company_id.id)]
        return action


class StockScrapBatchLine(models.Model):
    _name = 'stock.scrap.batch.line'
    _description = 'Línea de orden de bajas múltiple'

    batch_id = fields.Many2one(
        'stock.scrap.batch',
        string='Orden',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        related='batch_id.company_id',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        domain="[('type', 'in', ['product', 'consu'])]",
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lote/Serie',
        domain="[('product_id', '=', product_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    scrap_qty = fields.Float(
        string='Cantidad A la mano a dar de baja',
        required=True,
        digits='Product Unit of Measure',
        default=1.0,
    )
    expiration_date = fields.Datetime(
        related='lot_id.expiration_date',
        string='Caducidad',
        store=False,
        readonly=True,
    )
    purchase_lot_cost = fields.Monetary(
        string='Costo unitario',
        compute='_compute_purchase_lot_cost',
        store=True,
        currency_field='currency_id',
        readonly=True,
    )
    scrap_total_cost = fields.Monetary(
        string='Costo total',
        compute='_compute_scrap_total_cost',
        store=True,
        currency_field='currency_id',
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='UdM',
        related='product_id.uom_id',
        store=True,
        readonly=True,
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Ubicación Origen',
        related='batch_id.location_id',
        store=True,
        readonly=True,
    )
    scrap_location_id = fields.Many2one(
        'stock.location',
        string='Ubicación de bajas',
        related='batch_id.scrap_location_id',
        store=True,
        readonly=True,
    )
    scrap_reason_tag_ids = fields.Many2many(
        'stock.scrap.reason.tag',
        string='Motivo de baja',
        copy=True,
    )
    scrap_id = fields.Many2one(
        'stock.scrap',
        string='Baja generada',
        readonly=True,
        copy=False,
    )
    lot_qty_available = fields.Float(
        string='A la mano',
        compute='_compute_lot_qty_available',
        readonly=True,
    )

    @api.depends('lot_id', 'company_id')
    def _compute_lot_qty_available(self):
        for line in self:
            if line.lot_id:
                if hasattr(line.lot_id, 'qty_a_la_mano'):
                    line.lot_qty_available = line.lot_id.qty_a_la_mano
                else:
                    quants = self.env['stock.quant'].search([
                        ('lot_id', '=', line.lot_id.id),
                        ('company_id', '=', line.company_id.id),
                    ])
                    line.lot_qty_available = sum(quants.mapped('quantity'))
            else:
                line.lot_qty_available = 0.0

    @api.depends('company_id', 'product_id', 'lot_id', 'product_uom_id')
    def _compute_purchase_lot_cost(self):
        StockMove = self.env['stock.move']
        if 'purchase_line_id' not in StockMove._fields:
            for line in self:
                line.purchase_lot_cost = 0.0
            return

        StockMoveObj = self.env['stock.move'].sudo()
        lines = self.filtered(lambda line: line.product_id and line.lot_id and line.company_id)
        for line in self:
            line.purchase_lot_cost = 0.0
        if not lines:
            return

        for line in lines:
            # Find the first PO receipt move that brought this specific lot into inventory
            move = StockMoveObj.search([
                ('move_line_ids.lot_id', '=', line.lot_id.id),
                ('product_id', '=', line.product_id.id),
                ('state', '=', 'done'),
                ('picking_type_id.code', '=', 'incoming'),
                ('company_id', '=', line.company_id.id),
                ('purchase_line_id', '!=', False),
            ], order='date asc', limit=1)
            purchase_line = move.purchase_line_id if move else False
            line.purchase_lot_cost = (
                self._convert_purchase_lot_cost(purchase_line, line)
                if purchase_line
                else 0.0
            )

    @api.depends('purchase_lot_cost', 'scrap_qty')
    def _compute_scrap_total_cost(self):
        for line in self:
            line.scrap_total_cost = line.purchase_lot_cost * line.scrap_qty

    @api.model
    def _convert_purchase_lot_cost(self, purchase_line, line):
        if not purchase_line:
            return 0.0

        company = line.company_id or self.env.company
        company_currency = company.currency_id
        source_uom = purchase_line.product_uom_id or line.product_uom_id or line.product_id.uom_id
        target_uom = line.product_uom_id or line.product_id.uom_id
        amount = purchase_line.price_unit or 0.0

        if source_uom and target_uom and source_uom != target_uom:
            amount = source_uom._compute_price(amount, target_uom)

        source_currency = purchase_line.order_id.currency_id or company_currency
        if source_currency and company_currency and source_currency != company_currency:
            date = (
                purchase_line.order_id.date_approve
                or purchase_line.order_id.date_order
                or fields.Datetime.now()
            )
            amount = source_currency._convert(
                amount,
                company_currency,
                company,
                fields.Date.to_date(date),
            )

        return amount

    @api.constrains('scrap_qty')
    def _check_scrap_qty(self):
        for line in self:
            if line.scrap_qty <= 0:
                raise ValidationError(_('La cantidad A la mano a dar de baja debe ser mayor a cero.'))

    @api.constrains('lot_id', 'product_id')
    def _check_lot_product_match(self):
        for line in self:
            if line.lot_id and line.product_id and line.lot_id.product_id != line.product_id:
                raise ValidationError(_('El lote seleccionado no pertenece al producto de la línea.'))

    def _validate_line_data(self):
        self.ensure_one()
        if not self.product_id:
            raise UserError(_('La línea requiere un producto.'))
        if self.scrap_qty <= 0:
            raise UserError(_('La cantidad A la mano a dar de baja debe ser mayor a cero.'))
