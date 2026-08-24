import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseRouting(models.Model):
    """
    Sesión de enrutamiento de compras.
    Ciclo de vida: draft → calculated → confirmed → done
    """
    _name = 'purchase.routing'
    _description = 'Routing de Compras'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Referencia', required=True,
        default=lambda self: _('Nuevo'), copy=False, readonly=True,
    )
    date = fields.Date(
        string='Fecha', default=fields.Date.context_today,
        required=True, tracking=True,
    )
    user_id = fields.Many2one(
        'res.users', string='Responsable',
        default=lambda self: self.env.user, tracking=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Compañía',
        default=lambda self: self.env.company, required=True,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Almacén Destino',
        help='Almacén/sucursal que genera la demanda de reabastecimiento.',
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('calculated', 'Calculado'),
        ('confirmed', 'Confirmado'),
        ('done', 'POs Generadas'),
    ], string='Estado', default='draft', tracking=True, copy=False)

    # ── Configuración de routing ─────────────────────────────────────
    threshold_percent = fields.Float(
        string='Umbral de precio (%)',
        default=lambda self: self._default_threshold(),
        digits=(5, 2),
        tracking=True,
        help=(
            'Solo se reasigna al proveedor más barato si la diferencia de precio '
            'supera este porcentaje.\n'
            'Ejemplo: 6 → solo cambia de proveedor si el precio es al menos 6% más barato.'
        ),
    )
    po_initial_state = fields.Selection([
        ('draft', 'Borrador'),
        ('purchase', 'Confirmar automáticamente'),
    ], string='Estado inicial de OCs', default=lambda self: self._default_po_state(),
        required=True, tracking=True,
    )

    # ── Líneas y resultados ──────────────────────────────────────────
    line_ids = fields.One2many(
        'purchase.routing.line', 'routing_id', string='Líneas de Demanda',
    )
    po_ids = fields.Many2many('purchase.order', string='Órdenes de Compra', copy=False)
    notes = fields.Html(string='Notas')

    # ── Campos computados de resumen ─────────────────────────────────
    total_products = fields.Integer(compute='_compute_summary', store=True)
    total_qty_demanded = fields.Float(compute='_compute_summary', store=True)
    total_qty_satisfied = fields.Float(compute='_compute_summary', store=True)
    total_qty_unsatisfied = fields.Float(compute='_compute_summary', store=True)
    total_amount = fields.Float(compute='_compute_summary', store=True)
    po_count = fields.Integer(compute='_compute_po_count')
    all_detail_ids = fields.One2many(
        'purchase.routing.line.detail', 'routing_id',
        string='Todos los Detalles',
    )

    # ── Defaults desde parámetros de sistema ─────────────────────────
    def _default_threshold(self):
        return float(
            self.env['ir.config_parameter'].sudo().get_param(
                'purchase_smart_routing.threshold_percent', '6.0'
            )
        )

    def _default_po_state(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'purchase_smart_routing.po_initial_state', 'draft'
        )

    # ── Cómputos ─────────────────────────────────────────────────────
    @api.depends(
        'line_ids', 'line_ids.qty_demanded',
        'line_ids.qty_satisfied', 'line_ids.qty_unsatisfied',
        'line_ids.detail_ids.subtotal',
    )
    def _compute_summary(self):
        for routing in self:
            lines = routing.line_ids
            details = lines.mapped('detail_ids')
            routing.total_products = len(lines)
            routing.total_qty_demanded = sum(lines.mapped('qty_demanded'))
            routing.total_qty_satisfied = sum(lines.mapped('qty_satisfied'))
            routing.total_qty_unsatisfied = sum(lines.mapped('qty_unsatisfied'))
            routing.total_amount = sum(details.mapped('subtotal'))

    def _compute_po_count(self):
        for routing in self:
            routing.po_count = len(routing.po_ids)

    # ── Secuencia ────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('purchase.routing')
                    or _('Nuevo')
                )
        return super().create(vals_list)

    # ── Acciones de flujo ────────────────────────────────────────────
    def action_calculate(self):
        """Ejecuta el motor de routing sobre todas las líneas."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Agregue al menos una línea de demanda.'))

        threshold = self.threshold_percent / 100.0
        for line in self.line_ids:
            line.detail_ids.unlink()
            line._calculate_routing(threshold_pct=threshold)

        self.state = 'calculated'
        _logger.info(
            'Routing %s calculado: %d líneas, umbral=%.1f%%',
            self.name, len(self.line_ids), self.threshold_percent,
        )

    def action_reset_draft(self):
        self.ensure_one()
        self.line_ids.mapped('detail_ids').unlink()
        self.state = 'draft'

    def action_confirm(self):
        self.ensure_one()
        if self.state != 'calculated':
            raise UserError(_('Calcule el routing antes de confirmar.'))
        self.state = 'confirmed'

    def action_generate_pos(self):
        """Genera POs agrupadas por proveedor, respetando po_initial_state."""
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_('Confirme el routing antes de generar POs.'))

        details = self.line_ids.mapped('detail_ids').filtered(
            lambda d: d.qty_assigned > 0
        )
        if not details:
            raise UserError(_(
                'No hay cantidades asignadas. Recalcule el routing.'
            ))

        partners = details.mapped('partner_id')
        created_pos = self.env['purchase.order']

        for partner in partners:
            partner_details = details.filtered(lambda d: d.partner_id == partner)
            po_vals = self._prepare_po_vals(partner)
            po_vals['order_line'] = [
                (0, 0, self._prepare_po_line_vals(detail))
                for detail in partner_details
            ]
            po = self.env['purchase.order'].create(po_vals)

            if self.po_initial_state == 'purchase':
                po.button_confirm()

            created_pos |= po

        self.po_ids = [(6, 0, created_pos.ids)]
        self.state = 'done'

        _logger.info(
            'Routing %s: %d POs generadas (estado=%s)',
            self.name, len(created_pos), self.po_initial_state,
        )

        return {
            'name': _('Órdenes de Compra Generadas'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_pos.ids)],
            'context': {'create': False},
        }

    def action_view_pos(self):
        self.ensure_one()
        return {
            'name': _('Órdenes de Compra'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.po_ids.ids)],
        }

    # ── Helpers de construcción de vals ─────────────────────────────
    def _prepare_po_vals(self, partner):
        # sudo() is required: purchase users lack read access to stock.warehouse,
        # but this lookup is a system-level fallback, not a user security boundary.
        warehouse = self.warehouse_id or self.env['stock.warehouse'].sudo().search(
            [('company_id', '=', self.company_id.id)], limit=1
        )
        return {
            'partner_id': partner.id,
            'company_id': self.company_id.id,
            'origin': self.name,
            'date_order': fields.Datetime.now(),
            'picking_type_id': warehouse.in_type_id.id,
        }

    def _prepare_po_line_vals(self, detail):
        product = detail.line_id.product_id
        return {
            'product_id': product.id,
            'name': product.display_name,
            'product_qty': detail.qty_assigned,
            'price_unit': detail.price_unit,
            'product_uom': product.uom_po_id.id or product.uom_id.id,
            'date_planned': fields.Datetime.now(),
            'taxes_id': [(6, 0, product.supplier_taxes_id.ids)],
        }


class PurchaseRoutingLine(models.Model):
    """Producto + cantidad demandada dentro de una sesión de routing."""
    _name = 'purchase.routing.line'
    _description = 'Línea de Routing de Compra'
    _order = 'line_brand, product_name'

    routing_id = fields.Many2one(
        'purchase.routing', string='Routing',
        required=True, ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product', string='Producto', required=True,
    )
    product_name = fields.Char(related='product_id.name', store=True, string='Nombre')
    barcode = fields.Char(related='product_id.barcode', store=True, string='Código de Barras')
    default_code = fields.Char(
        related='product_id.default_code', store=True, string='Ref. Interna',
    )
    line_brand = fields.Char(
        string='Línea / Marca',
        help='Referencia de marca/línea del producto (ej. JALOMA, AMSA).',
    )
    qty_demanded = fields.Float(
        string='Cant. Demandada',
        digits='Product Unit of Measure',
        required=True,
    )
    source_partner_id = fields.Many2one(
        'res.partner', string='Proveedor Original',
        help=(
            'Proveedor de la OC fuente. Utilizado para la lógica de umbral: '
            'si la diferencia de precio con el más barato es menor al umbral configurado, '
            'se mantiene este proveedor en lugar de cambiar.'
        ),
    )

    detail_ids = fields.One2many(
        'purchase.routing.line.detail', 'line_id',
        string='Detalle por Proveedor',
    )

    # ── Campos computados ────────────────────────────────────────────
    qty_satisfied = fields.Float(
        compute='_compute_quantities', store=True, string='Cant. Asignada',
    )
    qty_unsatisfied = fields.Float(
        compute='_compute_quantities', store=True, string='Cant. Insatisfecha',
    )
    winner_partner_id = fields.Many2one(
        'res.partner', compute='_compute_quantities', store=True,
        string='Proveedor Ganador',
    )
    line_state = fields.Selection([
        ('none', 'Sin proveedor'),
        ('partial', 'Parcial'),
        ('fulfilled', 'Completa'),
    ], compute='_compute_quantities', store=True, string='Estado')
    notes = fields.Text(string='Notas de Routing')

    @api.depends('qty_demanded', 'detail_ids.qty_assigned')
    def _compute_quantities(self):
        for line in self:
            assigned = sum(line.detail_ids.mapped('qty_assigned'))
            line.qty_satisfied = assigned
            line.qty_unsatisfied = max(line.qty_demanded - assigned, 0.0)

            winner = line.detail_ids.filtered('is_winner')[:1]
            line.winner_partner_id = winner.partner_id if winner else False

            if assigned <= 0:
                line.line_state = 'none'
            elif assigned < line.qty_demanded:
                line.line_state = 'partial'
            else:
                line.line_state = 'fulfilled'

    def _calculate_routing(self, threshold_pct: float = 0.06):
        """
        Invoca el motor puro y persiste los resultados como
        purchase.routing.line.detail records.
        """
        self.ensure_one()
        from ..engines.routing_engine import SupplierOffer, allocate_product

        product = self.product_id

        # Buscar supplierinfo para este producto (variante o template)
        supplierinfos = self.env['product.supplierinfo'].search([
            '|',
            ('product_id', '=', product.id),
            '&',
            ('product_id', '=', False),
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
            ('effective_price', '>', 0),
        ])

        if not supplierinfos:
            self.notes = _('Sin catálogo de proveedor registrado para este producto.')
            return

        offers = [
            SupplierOffer(
                partner_id=si.partner_id.id,
                partner_name=si.partner_id.name,
                supplierinfo_id=si.id,
                effective_price=si.effective_price,
                available_stock=si.supplier_stock,
            )
            for si in supplierinfos
        ]

        result = allocate_product(
            product_id=product.id,
            qty_demanded=self.qty_demanded,
            offers=offers,
            current_partner_id=(
                self.source_partner_id.id if self.source_partner_id else None
            ),
            threshold_pct=threshold_pct,
        )

        if result.assignments:
            detail_vals_list = [
                {
                    'line_id': self.id,
                    'partner_id': a.partner_id,
                    'supplierinfo_id': a.supplierinfo_id,
                    'price_unit': a.price,
                    'supplier_stock': a.stock,
                    'qty_assigned': a.qty,
                    'is_winner': a.is_winner,
                    'rank': a.rank,
                    'motivo': a.motivo,
                }
                for a in result.assignments
            ]
            self.env['purchase.routing.line.detail'].create(detail_vals_list)

        self.notes = result.notes


class PurchaseRoutingLineDetail(models.Model):
    """Asignación de cantidad a un proveedor específico para una línea."""
    _name = 'purchase.routing.line.detail'
    _description = 'Detalle Routing por Proveedor'
    _order = 'rank'

    line_id = fields.Many2one(
        'purchase.routing.line', string='Línea',
        required=True, ondelete='cascade',
    )
    routing_id = fields.Many2one(
        related='line_id.routing_id', store=True,
    )
    product_id = fields.Many2one(
        related='line_id.product_id', store=True, string='Producto',
    )
    barcode = fields.Char(
        related='line_id.barcode', store=True, string='Código de Barras',
    )
    partner_id = fields.Many2one(
        'res.partner', string='Proveedor', required=True,
    )
    supplierinfo_id = fields.Many2one(
        'product.supplierinfo', string='Info Proveedor',
    )
    price_unit = fields.Float(
        string='Precio Unitario', digits='Product Price',
    )
    supplier_stock = fields.Float(
        string='Stock Proveedor', digits='Product Unit of Measure',
    )
    qty_assigned = fields.Float(
        string='Cant. Asignada', digits='Product Unit of Measure',
    )
    is_winner = fields.Boolean(string='Ganador')
    rank = fields.Integer(string='Ranking', default=0)
    motivo = fields.Char(string='Motivo')
    subtotal = fields.Float(
        compute='_compute_subtotal', store=True,
        string='Subtotal', digits='Product Price',
    )

    @api.depends('qty_assigned', 'price_unit')
    def _compute_subtotal(self):
        for detail in self:
            detail.subtotal = detail.qty_assigned * detail.price_unit
