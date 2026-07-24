from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    product_line_id = fields.Many2one(
        "md.product.line",
        string="Línea",
        help="Línea de producto propia de MDS, independiente de la Categoría estándar de Odoo.",
    )
