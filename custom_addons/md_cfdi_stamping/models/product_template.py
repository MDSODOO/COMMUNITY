from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_mx_clave_prod_serv = fields.Char(
        string='Clave Prod/Serv (SAT)',
        help='Código del catálogo c_ClaveProdServ del SAT, ej. 51102706 '
             'para medicamentos. Requerido para timbrar CFDI.',
    )
    l10n_mx_clave_unidad = fields.Char(
        string='Clave Unidad (SAT)',
        default='H87',
        help='Código del catálogo c_ClaveUnidad del SAT, ej. H87 = Pieza.',
    )
