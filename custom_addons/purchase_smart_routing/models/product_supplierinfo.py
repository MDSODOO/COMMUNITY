from odoo import api, fields, models


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    supplier_stock = fields.Float(
        string='Stock Proveedor',
        digits='Product Unit of Measure',
        default=0,
        help='Existencias a la mano en el almacén del proveedor. '
             'Se actualiza al importar su catálogo.',
    )
    supplier_stock_date = fields.Date(
        string='Fecha Actualización Stock',
        help='Fecha de la última actualización del inventario del proveedor.',
    )
    offer_price = fields.Float(
        string='Precio Oferta',
        digits='Product Price',
        help='Precio promocional temporal. Si está definido y es mayor a 0, '
             'se usa en lugar del precio estándar para el routing.',
    )
    offer_date_end = fields.Date(
        string='Vigencia Oferta',
        help='Fecha de fin de la oferta. Después de esta fecha se ignora.',
    )

    @api.depends('price', 'offer_price', 'offer_date_end')
    def _compute_effective_price(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if (rec.offer_price > 0
                    and rec.offer_date_end
                    and rec.offer_date_end >= today):
                rec.effective_price = rec.offer_price
            else:
                rec.effective_price = rec.price

    effective_price = fields.Float(
        string='Precio Efectivo',
        compute='_compute_effective_price',
        digits='Product Price',
        store=True,
        help='Precio que se usará para el routing: oferta vigente o precio estándar.',
    )
