from odoo import api, fields, models


class SupplierCostImportLog(models.Model):
    """Registro de auditoría de importaciones de costos"""
    _name = 'supplier.cost.import.log'
    _description = 'Registro de Importación de Costos de Proveedores'
    _order = 'date desc'

    date = fields.Datetime('Fecha de Importación', default=fields.Datetime.now, readonly=True)
    user_id = fields.Many2one('res.users', 'Usuario', default=lambda self: self.env.user, readonly=True)

    # Estadísticas
    total_rows = fields.Integer('Total de filas procesadas', readonly=True)
    updated = fields.Integer('Costos actualizados', readonly=True)
    not_found = fields.Integer('Productos no encontrados', readonly=True)
    errors = fields.Integer('Errores de procesamiento', readonly=True)

    # Detalle de líneas
    log_lines = fields.One2many('supplier.cost.import.log.line', 'log_id', copy=False, readonly=True)

    # Archivo original (attachment)
    original_file = fields.Binary('Archivo original', attachment=True, readonly=True)
    original_filename = fields.Char('Nombre del archivo', readonly=True)

    # Resumen
    summary = fields.Text('Resumen de importación', readonly=True)


class SupplierCostImportLogLine(models.Model):
    """Líneas de detalle de cada importación"""
    _name = 'supplier.cost.import.log.line'
    _description = 'Línea de Importación de Costos'
    _order = 'row_number'

    log_id = fields.Many2one('supplier.cost.import.log', ondelete='cascade', required=True)

    row_number = fields.Integer('Número de fila', readonly=True)
    barcode = fields.Char('Código de barras', readonly=True, index=True)
    product_name = fields.Char('Descripción del producto', readonly=True)

    # Producto encontrado
    product_id = fields.Many2one('price.comparison.product', 'Producto', readonly=True)

    # Valores
    old_cost = fields.Float('Costo anterior', readonly=True, digits=(12, 2))
    new_cost = fields.Float('Costo nuevo', readonly=True, digits=(12, 2))
    cost_change = fields.Float('Cambio', compute='_compute_cost_change', readonly=True, digits=(12, 2))

    # Estado
    status = fields.Selection([
        ('updated', 'Actualizado'),
        ('not_found', 'Producto no encontrado'),
        ('error', 'Error de procesamiento'),
    ], 'Estado', readonly=True, index=True)

    error_message = fields.Char('Mensaje de error', readonly=True)

    @api.depends('old_cost', 'new_cost')
    def _compute_cost_change(self):
        for record in self:
            if record.old_cost:
                record.cost_change = record.new_cost - record.old_cost
            else:
                record.cost_change = record.new_cost if record.new_cost else 0.0
