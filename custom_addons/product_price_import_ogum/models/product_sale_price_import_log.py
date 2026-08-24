# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductSalePriceImportLog(models.Model):
    """Registro auditable / Auditable record for sale price imports."""
    _name = 'product.sale.price.import.log'
    _description = 'Registro de Importación de Precios de Venta'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Referencia / Reference',
        compute='_compute_name',
        store=True,
    )
    date = fields.Datetime(
        string='Fecha / Date',
        default=fields.Datetime.now,
        readonly=True,
        tracking=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Usuario / User',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    apply_mode = fields.Selection(
        [
            ('base', 'Precio de venta base / Base Sale Price'),
            ('pricelist', 'Lista de precios / Pricelist'),
        ],
        string='Destino / Target',
        readonly=True,
        tracking=True,
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Lista de precios / Pricelist',
        readonly=True,
        tracking=True,
    )
    original_file = fields.Binary(
        string='Archivo original / Original File',
        attachment=True,
        readonly=True,
    )
    original_filename = fields.Char(
        string='Nombre del archivo / Filename',
        readonly=True,
    )
    total_rows = fields.Integer(
        string='Filas procesadas / Processed Rows',
        readonly=True,
        tracking=True,
    )
    updated_count = fields.Integer(
        string='Precios actualizados / Updated Prices',
        readonly=True,
        tracking=True,
    )
    skipped_count = fields.Integer(
        string='Filas omitidas / Skipped Rows',
        readonly=True,
        tracking=True,
    )
    error_count = fields.Integer(
        string='Filas con error / Error Rows',
        readonly=True,
        tracking=True,
    )
    summary = fields.Text(
        string='Resumen / Summary',
        readonly=True,
    )
    line_ids = fields.One2many(
        'product.sale.price.import.log.line',
        'log_id',
        string='Detalle / Details',
        readonly=True,
        copy=False,
    )

    @api.depends('date', 'original_filename')
    def _compute_name(self):
        for record in self:
            date_label = fields.Datetime.to_string(record.date) if record.date else ''
            name = record.original_filename or 'Excel'
            record.name = f'{date_label} - {name}'.strip(' -')


class ProductSalePriceImportLogLine(models.Model):
    """Detalle por fila / Per-row import detail."""
    _name = 'product.sale.price.import.log.line'
    _description = 'Línea de Importación de Precios de Venta'
    _order = 'row_number, id'

    log_id = fields.Many2one(
        'product.sale.price.import.log',
        string='Log',
        required=True,
        ondelete='cascade',
    )
    row_number = fields.Integer(
        string='Fila / Row',
        readonly=True,
    )
    sku = fields.Char(
        string='SKU',
        readonly=True,
        index=True,
    )
    barcode = fields.Char(
        string='Código de barras / Barcode',
        readonly=True,
        index=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Producto / Product',
        readonly=True,
        index=True,
    )
    product_name = fields.Char(
        string='Nombre / Name',
        readonly=True,
    )
    old_price = fields.Float(
        string='Precio anterior / Previous Price',
        digits='Product Price',
        readonly=True,
    )
    new_price = fields.Float(
        string='Precio nuevo / New Price',
        digits='Product Price',
        readonly=True,
    )
    status = fields.Selection(
        [
            ('updated', 'Actualizado / Updated'),
            ('skipped', 'Omitido / Skipped'),
            ('error', 'Error'),
        ],
        string='Estado / Status',
        readonly=True,
        index=True,
    )
    error_message = fields.Char(
        string='Detalle / Detail',
        readonly=True,
    )
