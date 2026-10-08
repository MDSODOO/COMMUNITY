from odoo import api, fields, models


class ResPartnerProviderProfile(models.Model):
    _inherit = 'res.partner'

    pdf_lot_provider_key = fields.Selection(
        selection='_get_pdf_lot_provider_selection',
        string='Perfil de lotes PDF',
        help='Estrategia usada para extraer lotes y caducidades de PDFs de este proveedor.',
    )

    cfdi_supplier_format = fields.Selection([
        ('brudifarma', 'BRUDIFARMA'),
        ('quifamesa', 'QUIFAMESA'),
    ], string='Formato CFDI',
        help='Estrategia de parseo para importar facturas CFDI de este proveedor. '
             'Solo los proveedores con este campo configurado aparecen como opciones '
             'al importar un XML en Compras.',
    )

    @api.model
    def _get_pdf_lot_provider_selection(self):
        from ..services.pdf_lot_provider import available_providers
        return available_providers()
