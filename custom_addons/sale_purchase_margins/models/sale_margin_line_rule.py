# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .margin_tools import normalize_margin_key


class SaleMarginLineRule(models.Model):
    _name = 'qfm.sale.margin.line.rule'
    _description = 'Regla de margen por linea de producto'
    _order = 'company_id, line_name'

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        index=True,
        help='Compañía a la que aplica esta regla de margen.',
    )

    line_name = fields.Char(
        string='Linea del producto',
        required=True,
        index=True,
    )
    line_key = fields.Char(
        string='Clave normalizada',
        compute='_compute_line_key',
        store=True,
        readonly=True,
        index=True,
    )
    margin_pct = fields.Float(
        string='Margen objetivo (%)',
        required=True,
        digits=(16, 2),
    )
    active = fields.Boolean(default=True)

    _qfm_sale_margin_line_rule_line_key_company_uniq = models.Constraint(
        'UNIQUE(company_id, line_key)',
        'Ya existe una regla para esa linea de producto en esta compañía.',
    )

    @api.depends('line_name')
    def _compute_line_key(self):
        for rec in self:
            rec.line_key = normalize_margin_key(rec.line_name)

    @api.constrains('line_name')
    def _check_line_name(self):
        for rec in self:
            if not normalize_margin_key(rec.line_name):
                raise ValidationError('La linea del producto no puede quedar vacia.')

    @api.constrains('line_key', 'company_id')
    def _check_company_scoped_uniqueness(self):
        """Evita duplicados también cuando company_id es NULL (fallback global)."""
        for rec in self.filtered(lambda r: r.line_key and not r.company_id):
            duplicates = self.search_count([
                ('id', '!=', rec.id),
                ('line_key', '=', rec.line_key),
                ('company_id', '=', False),
            ])
            if duplicates:
                raise ValidationError(
                    'Ya existe una regla global para esa linea de producto.'
                )

    @api.constrains('margin_pct')
    def _check_margin_pct(self):
        for rec in self:
            if rec.margin_pct < 0.0 or rec.margin_pct >= 100.0:
                raise ValidationError(
                    'El margen objetivo debe estar entre 0 y menor que 100%.'
                )

    @api.model
    def get_margin_for_line_name(self, line_name, company=None):
        line_key = normalize_margin_key(line_name)
        if not line_key:
            return False

        target_company = company or self.env.company
        domain = [
            ('active', '=', True),
            ('line_key', '=', line_key),
            ('company_id', 'in', [target_company.id, False] if target_company else [False]),
        ]
        rules = self.search(domain)
        if not rules:
            return False

        company_rule = rules.filtered(lambda r: r.company_id)
        return (company_rule[:1] or rules[:1]).margin_pct
