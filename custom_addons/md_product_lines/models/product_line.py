from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductLine(models.Model):
    _name = "md.product.line"
    _description = "Línea de Producto (independiente de product.category)"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    legacy_ref = fields.Char(
        string="Referencia legacy",
        help="Traza al origen (ej. MICROSIP-LINEA-<id>) para migraciones idempotentes.",
    )
    product_tmpl_ids = fields.One2many(
        "product.template", "product_line_id", string="Productos"
    )
    product_count = fields.Integer(compute="_compute_product_count")
    parent_line_id = fields.Many2one(
        "md.product.line", string="Línea Principal",
        help="Línea/distribuidor principal del que esta es una sublínea "
             "(ej. 'JAYOR' es principal de 'SENSIMEDICAL', 'SKINPROT', etc.). "
             "Permite mantener el nombre de la línea corto en los productos.",
    )
    sublinea_ids = fields.One2many(
        "md.product.line", "parent_line_id", string="Sublíneas"
    )
    sublinea_count = fields.Integer(compute="_compute_sublinea_count")

    def _compute_product_count(self):
        for line in self:
            line.product_count = len(line.product_tmpl_ids)

    def _compute_sublinea_count(self):
        for line in self:
            line.sublinea_count = len(line.sublinea_ids)

    @api.constrains('parent_line_id')
    def _check_parent_line_recursion(self):
        if not self._check_recursion(parent='parent_line_id'):
            raise ValidationError("No se permite crear una jerarquía circular de líneas.")

    _legacy_ref_uniq = models.Constraint(
        "UNIQUE(legacy_ref)", "Ya existe una línea con esa referencia legacy."
    )
