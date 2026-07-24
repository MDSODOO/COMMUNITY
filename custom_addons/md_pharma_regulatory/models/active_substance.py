from odoo import fields, models


class MdActiveSubstance(models.Model):
    _name = 'md.active.substance'
    _description = 'Sustancia Activa (homologación COFEPRIS)'
    _order = 'name'

    name = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color')
    product_ids = fields.Many2many(
        'product.template', 'md_product_active_substance_rel',
        'substance_id', 'product_tmpl_id',
        string='Productos',
    )
    product_count = fields.Integer(compute='_compute_product_count')

    _name_uniq = models.Constraint('UNIQUE(name)', 'Ya existe una sustancia activa con ese nombre.')

    def _compute_product_count(self):
        for rec in self:
            rec.product_count = len(rec.product_ids)
