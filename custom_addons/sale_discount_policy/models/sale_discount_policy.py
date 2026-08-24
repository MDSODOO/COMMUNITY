from odoo import models, fields


class SaleDiscountPolicy(models.Model):
    _name = 'sale.discount.policy'
    _description = 'Farmacias Económicas Discount Policy'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Policy Name',
        required=True,
        default='Política 2% Farmacias Económicas',
    )
    active = fields.Boolean(default=True)
    discount_pct = fields.Float(
        string='Discount (%)',
        default=2.0,
        digits=(5, 2),
        help='Base discount percentage applied to qualifying customers.',
    )

    partner_ids = fields.Many2many(
        'res.partner',
        string='Beneficiary Partners',
        help='Partners that are eligible for this discount policy.',
    )
    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        string='Authorized Branches',
        help='Policy applies only in these warehouses. Empty = all warehouses.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    _company_uniq = models.Constraint(
        'UNIQUE(company_id)',
        'Only one active discount policy per company is allowed.',
    )
