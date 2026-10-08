from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    md_mail_account_ids = fields.One2many('md.mail.account', 'user_id',
                                           string='Cuentas de Correo')
