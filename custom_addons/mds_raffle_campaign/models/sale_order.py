from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Hoy casi todo pasa por 'backend' (captura manual del vendedor; ver
    # auditoría 2026-08-07: solo 5/1811 pedidos históricos traen website_id).
    # El futuro conector B2B (Next.js) debe pasar origin_channel='b2b_online'
    # explícito al crear el pedido vía API. Si en cambio el pedido llega por
    # el checkout nativo de website_sale, website_id ya viene seteado y se
    # usa como señal de respaldo automática.
    origin_channel = fields.Selection([
        ('backend', 'Backoffice'),
        ('b2b_online', 'B2B Online'),
    ], string='Canal de Origen', default='backend')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('origin_channel') and vals.get('website_id'):
                vals['origin_channel'] = 'b2b_online'
        return super().create(vals_list)

    def action_confirm(self):
        res = super().action_confirm()
        self.env['raffle.campaign']._evaluate_order_for_tickets(self)
        return res
