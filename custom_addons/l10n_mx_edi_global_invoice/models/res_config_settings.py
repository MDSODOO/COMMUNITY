import logging
import decimal
from collections import defaultdict

from odoo import _, api, Command, fields, models
from lxml import etree
import logging
_logger = logging.getLogger(__name__)

class CompanySettingsInherit(models.Model):
    _inherit = 'res.company'

    partner_inv_global_id = fields.Many2one("res.partner", string="Cliente Factura Global", default=lambda self: self.env['res.partner'].search([('name','ilike','PUBLICO EN GENERAL')],limit=1).id )
    journal_inv_global_id = fields.Many2one("account.journal", string="Diario Factura Global",domain=[('type','=','sale')])


class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    partner_inv_global_id = fields.Many2one("res.partner", string="Cliente Factura Global", related='company_id.partner_inv_global_id',
                                  readonly=False)
    journal_inv_global_id = fields.Many2one("account.journal", string="Diario Factura Global", related='company_id.journal_inv_global_id',
                                  readonly=False)

    ### Campos predeterminados por punto de venta
    pos_partner_global_id = fields.Many2one(
        related='pos_config_id.partner_global_id',
        string="Cliente Factura Global (POS)",
        readonly=False,
    )
    pos_journal_global_id = fields.Many2one(
        related='pos_config_id.journal_global_id',
        string="Diario Factura Global (POS)",
        readonly=False,
    )
    pos_active_facturacion_global = fields.Boolean(related='pos_config_id.active_facturacion_global', readonly=False)
