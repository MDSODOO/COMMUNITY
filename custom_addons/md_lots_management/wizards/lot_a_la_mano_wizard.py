from odoo import fields, models


class LotALaManoWizard(models.TransientModel):
    _name = 'md.lot.a.la.mano.wizard'
    _description = 'A la mano'

    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        string='Lote',
        required=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        related='lot_id.product_id',
        string='Producto',
        readonly=True,
    )
    cantidad_entrada_a_la_mano = fields.Float(
        string='A la mano',
        required=True,
        help='A la mano',
    )
    ubicacion_destino_id = fields.Many2one(
        comodel_name='stock.location',
        string='Ubicación destino',
        required=True,
        domain=[('usage', '=', 'internal')],
    )

    def action_apply_a_la_mano(self):
        self.ensure_one()
        return self.lot_id._md_apply_a_la_mano_quantity(
            self.cantidad_entrada_a_la_mano,
            self.ubicacion_destino_id,
        )
