# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PriceComparisonProduct(models.Model):
    _name = 'price.comparison.product'
    _description = 'Producto Base para Comparación de Precios'
    _rec_name = 'name'
    _order = 'name'

    barcode = fields.Char('Código de Barras', required=True, index=True)
    name = fields.Char('Producto', required=True)
    brand = fields.Char('Marca / Laboratorio')
    # Step 26: costo visible solo para analistas de precios
    quifa_cost = fields.Float('Costo Quifamesa', digits=(12, 2))
    line_ids = fields.One2many(
        'price.comparison.line', 'product_id', string='Precios Proveedores')
    # Step 2 (P2-3 fix): cuenta proveedores únicos, no líneas
    supplier_count = fields.Integer(compute='_compute_supplier_count', store=True)
    best_price = fields.Float(
        'Mejor Precio', compute='_compute_best_price', store=True, digits=(12, 2))
    best_supplier_id = fields.Many2one(
        'res.partner', string='Mejor Proveedor',
        compute='_compute_best_price', store=True)

    _barcode_uniq = models.Constraint(
        'unique (barcode)',
        'Ya existe un producto con este código de barras.',
    )

    @api.depends('barcode', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.barcode}] {rec.name}" if rec.barcode else (rec.name or '')

    @api.depends('line_ids.supplier_id')
    def _compute_supplier_count(self):
        for rec in self:
            rec.supplier_count = len(rec.line_ids.mapped('supplier_id'))

    # Step 17: batch SQL — 1 query para todo el recordset en lugar de N iteraciones
    @api.depends('line_ids.price', 'line_ids.supplier_id')
    def _compute_best_price(self):
        if not self.ids:
            return
        self.env.cr.execute("""
            SELECT DISTINCT ON (product_id)
                product_id, supplier_id, price
            FROM price_comparison_line
            WHERE product_id IN %s AND price > 0
            ORDER BY product_id, price ASC
        """, [tuple(self.ids)])
        rows = {row[0]: (row[1], row[2]) for row in self.env.cr.fetchall()}
        for rec in self:
            if rec.id in rows:
                supplier_id, price = rows[rec.id]
                rec.best_price = price
                rec.best_supplier_id = supplier_id
            else:
                rec.best_price = 0.0
                rec.best_supplier_id = False

    # Step 10: acción para smart button
    def action_view_price_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Precios — %s') % self.name,
            'res_model': 'price.comparison.line',
            'view_mode': 'list,pivot',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
            'target': 'current',
        }


class PriceComparisonLine(models.Model):
    _name = 'price.comparison.line'
    _description = 'Línea de Precio por Proveedor'
    # Step 4: ordenación por defecto — mejor precio primero, luego precio asc
    _order = 'is_best desc, price asc'

    # P0-1: restricción única compuesta
    _product_supplier_uniq = models.Constraint(
        'unique (product_id, supplier_id)',
        'Ya existe un precio de este proveedor para el mismo producto.',
    )

    product_id = fields.Many2one(
        'price.comparison.product', string='Producto',
        required=True, ondelete='cascade', index=True)
    barcode = fields.Char(related='product_id.barcode', store=True, index=True)
    product_name = fields.Char(related='product_id.name', store=True, string='Producto')
    brand = fields.Char(related='product_id.brand', store=True, string='Marca')
    quifa_cost = fields.Float(
        related='product_id.quifa_cost', store=True,
        string='Costo Quifamesa', digits=(12, 2))

    # Step 6: group_expand fuerza columnas de todos los proveedores activos en pivot
    supplier_id = fields.Many2one(
        'res.partner', string='Proveedor', required=True,
        ondelete='restrict',
        index=True, group_expand='_group_expand_supplier_ids')
    supplier_name = fields.Char(related='supplier_id.name', store=True, string='Proveedor')

    price = fields.Float('Precio Proveedor', digits=(12, 4))
    # Step 2: cantidad A la mano del proveedor.
    supplier_qty_on_hand = fields.Float('A la mano (Proveedor)', digits=(12, 0))
    # Step 3: días de entrega para comparar agilidad
    lead_time = fields.Integer('Días de Entrega')

    price_diff = fields.Float(
        'Diferencia ($)', compute='_compute_diff', store=True, digits=(12, 2))
    price_diff_pct = fields.Float(
        'Diferencia (%)', compute='_compute_diff', store=True, digits=(12, 2))
    # Step 8: ahorro vs costo base (medida en pivot)
    savings_vs_quifa = fields.Float(
        'Ahorro vs Quifamesa', compute='_compute_savings', store=True, digits=(12, 2))

    # Step 18: índice en is_best para acelerar filtros y pivot
    is_best = fields.Boolean('Mejor Precio', compute='_compute_is_best', store=True, index=True)
    import_date = fields.Date('Fecha de Importación', default=fields.Date.today)
    catalog_name = fields.Char('Catálogo Origen')
    # Step 15: flag computado para alerta de antigüedad > 30 días
    catalog_is_stale = fields.Boolean(
        'Catálogo Desactualizado', compute='_compute_catalog_is_stale', store=True)

    # Step 6: expande pivot para mostrar todos los proveedores activos como columnas
    @api.model
    def _group_expand_supplier_ids(self, suppliers, domain, order):
        return self.env['res.partner'].search(
            [('supplier_rank', '>', 0), ('active', '=', True)],
            order=order or 'name asc',
            limit=60,
        )

    @api.depends('price', 'quifa_cost')
    def _compute_diff(self):
        for rec in self:
            if rec.quifa_cost and rec.price:
                rec.price_diff = rec.price - rec.quifa_cost
                rec.price_diff_pct = (
                    (rec.price - rec.quifa_cost) / rec.quifa_cost
                ) * 100
            else:
                rec.price_diff = 0.0
                rec.price_diff_pct = 0.0

    # Step 8
    @api.depends('price', 'quifa_cost')
    def _compute_savings(self):
        for rec in self:
            rec.savings_vs_quifa = (
                rec.quifa_cost - rec.price
                if rec.quifa_cost and rec.price else 0.0
            )

    @api.depends('price', 'product_id.line_ids.price')
    def _compute_is_best(self):
        for rec in self:
            if not rec.price:
                rec.is_best = False
                continue
            siblings = rec.product_id.line_ids.filtered(lambda l: l.price > 0)
            rec.is_best = bool(siblings) and rec.price <= min(siblings.mapped('price'))

    # Step 15
    @api.depends('import_date')
    def _compute_catalog_is_stale(self):
        today = fields.Date.today()
        for rec in self:
            if rec.import_date:
                rec.catalog_is_stale = (today - rec.import_date).days > 30
            else:
                rec.catalog_is_stale = False

    # Step 25: validación a nivel de aplicación para unicidad compuesta
    # (complementa la restricción SQL ante cargas concurrentes)
    @api.model_create_multi
    def create(self, vals_list):
        if not vals_list:
            return self.browse()
        pairs = {
            (v['product_id'], v['supplier_id'])
            for v in vals_list
            if v.get('product_id') and v.get('supplier_id')
        }
        if pairs:
            p_ids = list({p[0] for p in pairs})
            s_ids = list({p[1] for p in pairs})
            existing = self.search([
                ('product_id', 'in', p_ids),
                ('supplier_id', 'in', s_ids),
            ])
            existing_set = {(r.product_id.id, r.supplier_id.id) for r in existing}
            vals_list = [
                v for v in vals_list
                if (v.get('product_id'), v.get('supplier_id')) not in existing_set
            ]
        return super().create(vals_list) if vals_list else self.browse()

    # Step 27: registrar historial cuando cambia el precio
    def write(self, vals):
        if 'price' in vals and not self.env.context.get('import_no_history'):
            history_vals = [
                {
                    'line_id': rec.id,
                    'old_price': rec.price,
                    'new_price': vals['price'],
                }
                for rec in self if rec.price != vals['price']
            ]
            res = super().write(vals)
            if history_vals:
                self.env['price.comparison.history'].sudo().create(history_vals)
            return res
        return super().write(vals)


# Step 27: modelo de auditoría de cambios de precio
class PriceComparisonHistory(models.Model):
    _name = 'price.comparison.history'
    _description = 'Historial de Cambios de Precio'
    _order = 'date desc'

    line_id = fields.Many2one(
        'price.comparison.line', string='Línea',
        ondelete='cascade', index=True, required=True)
    product_id = fields.Many2one(
        related='line_id.product_id', store=True, string='Producto',
        ondelete='set null')
    supplier_id = fields.Many2one(
        related='line_id.supplier_id', store=True, string='Proveedor',
        ondelete='set null')
    old_price = fields.Float('Precio Anterior', digits=(12, 2), readonly=True)
    new_price = fields.Float('Precio Nuevo', digits=(12, 2), readonly=True)
    price_change = fields.Float(
        'Cambio ($)', compute='_compute_change', store=True, digits=(12, 2))
    user_id = fields.Many2one(
        'res.users', string='Usuario',
        default=lambda self: self.env.user, readonly=True)
    date = fields.Datetime('Fecha', default=fields.Datetime.now, readonly=True)

    @api.depends('old_price', 'new_price')
    def _compute_change(self):
        for rec in self:
            rec.price_change = rec.new_price - rec.old_price
