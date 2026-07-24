from odoo import _, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'portal.mixin']
    _description = 'Stock Picking (portal access + tracking)'

    def _compute_access_url(self):
        super()._compute_access_url()
        for picking in self:
            picking.access_url = f'/my/pickings/{picking.id}'

    def send_to_shipper(self):
        self.ensure_one()
        try:
            return super().send_to_shipper()
        except TypeError as exc:
            carrier_name = self.carrier_id.name if self.carrier_id else _('desconocido')
            raise UserError(
                _(
                    "El transportista «%(carrier)s» devolvió una respuesta vacía al intentar "
                    "generar la guía de envío. Verifica la configuración e integración del "
                    "proveedor de paquetería."
                ) % {'carrier': carrier_name}
            ) from exc
