# -*- coding: utf-8 -*-
from odoo import fields, models


class MobileDevice(models.Model):
    _name = 'medicine.depot.mobile.device'
    _description = 'Dispositivo móvil registrado para push notifications (Expo)'
    _rec_name = 'push_token'

    # Nombre de modelo propio (medicine.depot.mobile.device), no
    # res.users.device -- referencia de patrón tomada de quifamesa_mobile_api
    # (misma forma: user_id + push_token + platform + constraint unique),
    # pero sin compartir nombre de modelo/tabla ni depender de ese addon.
    user_id = fields.Many2one('res.users', string='Usuario', required=True, ondelete='cascade', index=True)
    push_token = fields.Char(string='Expo Push Token', required=True, index=True)
    platform = fields.Selection([('ios', 'iOS'), ('android', 'Android')], string='Plataforma', required=True)
    device_name = fields.Char(string='Nombre del dispositivo')
    active = fields.Boolean(string='Activo', default=True)
    last_seen = fields.Datetime(string='Último registro', default=fields.Datetime.now)

    _push_token_uniq = models.Constraint(
        'unique(push_token)',
        'Este token de push ya está registrado.',
    )
