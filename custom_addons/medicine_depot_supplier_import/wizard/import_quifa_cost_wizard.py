import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.quifa_cost_parser import QuifaCostParser

_logger = logging.getLogger(__name__)


class SupplierCostImportWizard(models.TransientModel):
    """Wizard para importar y actualizar costos desde Excel"""
    _name = 'supplier.cost.import.wizard'
    _description = 'Importar Costos de Proveedores desde Excel'

    # ============================================================
    # CAMPOS DE CARGA DE ARCHIVO
    # ============================================================
    file = fields.Binary('Archivo Excel', required=True, help='Archivo en formato .xlsx o .xls')
    filename = fields.Char('Nombre del Archivo')

    # ============================================================
    # CONFIGURACIÓN DE COLUMNAS (flexible)
    # ============================================================
    col_barcode = fields.Char(
        'Columna Código de Barras',
        default='A',
        required=True,
        help='Letra de columna (A, B, C...) o nombre del encabezado'
    )
    col_cost = fields.Char(
        'Columna Costo Unitario',
        default='H',
        required=True,
        help='Letra de columna o nombre del encabezado con el costo a actualizar'
    )
    col_name = fields.Char(
        'Columna Descripción/Artículo',
        default='C',
        help='Letra o nombre del encabezado con la descripción del producto'
    )
    header_row = fields.Integer(
        'Fila de Encabezados',
        default=1,
        required=True,
        help='Número de fila donde están los encabezados (1 = primera fila)'
    )

    # ============================================================
    # MODO DE OPERACIÓN
    # ============================================================
    mode = fields.Selection([
        ('preview', 'Previsualizar cambios (sin guardar)'),
        ('update', 'Actualizar costos en el sistema'),
    ], string='Modo', default='preview', required=True,
        help='En modo preview, puedes revisar los cambios antes de aplicarlos')

    # ============================================================
    # RESULTADOS
    # ============================================================
    result_message = fields.Text('Resultado', readonly=True)
    preview_lines = fields.One2many(
        'supplier.cost.import.wizard.line',
        'wizard_id',
        'Líneas para importar',
        readonly=True
    )

    # ============================================================
    # COMPUTED FIELDS
    # ============================================================
    total_lines = fields.Integer(
        'Total de líneas',
        compute='_compute_statistics',
        store=False
    )
    valid_lines = fields.Integer(
        'Líneas válidas',
        compute='_compute_statistics',
        store=False
    )
    error_lines = fields.Integer(
        'Líneas con error',
        compute='_compute_statistics',
        store=False
    )
    products_to_update = fields.Integer(
        'Productos a actualizar',
        compute='_compute_statistics',
        store=False
    )
    products_not_found = fields.Integer(
        'Productos no encontrados',
        compute='_compute_statistics',
        store=False
    )

    # ============================================================
    # COMPUTADOS
    # ============================================================
    @api.depends('preview_lines.status', 'preview_lines.product_id')
    def _compute_statistics(self):
        """Calcula estadísticas de las líneas"""
        for wizard in self:
            lines = wizard.preview_lines
            wizard.total_lines = len(lines)
            wizard.valid_lines = len(lines.filtered(lambda l: l.status == 'ok'))
            wizard.error_lines = len(lines.filtered(lambda l: l.status in ('invalid_cost', 'no_barcode', 'error')))
            wizard.products_to_update = len(lines.filtered(lambda l: l.status == 'ok' and l.product_id))
            wizard.products_not_found = len(lines.filtered(lambda l: l.status == 'ok' and not l.product_id))

    # ============================================================
    # ACCIONES PRINCIPALES
    # ============================================================
    def action_preview(self):
        """Analiza el archivo sin guardar cambios"""
        self.ensure_one()

        if not self.file:
            raise UserError(_('Selecciona un archivo Excel.'))

        # Parseador
        parser = QuifaCostParser(self.env)

        # Parsear archivo
        try:
            parse_result = parser.parse(
                file_binary=self.file,
                filename=self.filename,
                col_barcode=self.col_barcode,
                col_cost=self.col_cost,
                col_name=self.col_name,
                header_row=self.header_row,
            )
        except UserError as exc:
            raise UserError(f'Error al procesar el archivo: {exc}')

        # Limpiar líneas previas
        self.preview_lines.unlink()

        # Pre-cargar todos los productos válidos en un dict (1 sola query)
        valid_barcodes = [
            l.barcode for l in parse_result.lines
            if l.status == 'ok' and l.barcode
        ]
        products_by_barcode = {}
        if valid_barcodes:
            for p in self.env['price.comparison.product'].search(
                [('barcode', 'in', valid_barcodes)]
            ):
                products_by_barcode[p.barcode] = p

        preview_lines_data = []

        for parse_line in parse_result.lines:
            # Si la línea no es válida, crear línea de error
            if parse_line.status != 'ok':
                preview_lines_data.append({
                    'wizard_id': self.id,
                    'row_number': parse_line.row_number,
                    'barcode': parse_line.barcode,
                    'product_name': parse_line.product_name or '',
                    'new_cost': 0.0,
                    'status': parse_line.status,
                    'error_message': parse_line.error or '',
                })
                continue

            # Línea válida: producto ya en caché
            product = products_by_barcode.get(parse_line.barcode)

            if product:
                preview_lines_data.append({
                    'wizard_id': self.id,
                    'row_number': parse_line.row_number,
                    'barcode': parse_line.barcode,
                    'product_name': parse_line.product_name or product.name,
                    'product_id': product.id,
                    'old_cost': product.quifa_cost,
                    'new_cost': parse_line.cost,
                    'status': 'ok',
                })
            else:
                # Producto no encontrado
                preview_lines_data.append({
                    'wizard_id': self.id,
                    'row_number': parse_line.row_number,
                    'barcode': parse_line.barcode,
                    'product_name': parse_line.product_name or f'Producto {parse_line.barcode}',
                    'new_cost': parse_line.cost,
                    'status': 'not_found',
                    'error_message': 'No encontrado en catálogo base',
                })

        # Crear todas las líneas
        if preview_lines_data:
            self.env['supplier.cost.import.wizard.line'].create(preview_lines_data)

        # Mensage de resultado
        self.result_message = (
            f'✅ Análisis completado\n\n'
            f'Total de líneas: {parse_result.total}\n'
            f'Líneas válidas: {parse_result.valid}\n'
            f'Productos a actualizar: {self.products_to_update}\n'
            f'Productos no encontrados: {self.products_not_found}\n'
            f'Errores: {self.error_lines}\n\n'
            f'Revisa los cambios en la tabla de abajo. '
            f'Cuando estés listo, cambia el modo a "Actualizar" y haz clic en "Importar".'
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_import(self):
        """Importa y actualiza costos en el sistema"""
        self.ensure_one()

        if not self.preview_lines:
            raise UserError(_('No hay líneas para importar. Ejecuta primero "Vista previa".'))

        # Filtrar líneas válidas
        lines_to_update = self.preview_lines.filtered(
            lambda l: l.status == 'ok' and l.product_id
        )

        if not lines_to_update:
            raise UserError(
                _('No hay productos válidos para actualizar. '
                  'Verifica que haya productos encontrados en el catálogo.')
            )

        # Crear log de importación
        log_vals = {
            'user_id': self.env.user.id,
            'original_file': self.file,
            'original_filename': self.filename,
            'total_rows': len(self.preview_lines),
        }

        log_lines_data = []
        updated_count = 0
        not_found_count = 0
        error_count = 0

        # Mapeo wizard status → log status (modelos con Selection distintas)
        _STATUS_MAP = {
            'ok': 'updated',
            'not_found': 'not_found',
            'no_barcode': 'error',
            'invalid_cost': 'error',
            'error': 'error',
        }

        # Construir log_lines_data con todos los registros (incluye errores previos al write)
        for line in self.preview_lines:
            log_line_vals = {
                'row_number': line.row_number,
                'barcode': line.barcode,
                'product_name': line.product_name,
                'status': _STATUS_MAP.get(line.status, 'error'),
                'error_message': line.error_message,
                'new_cost': line.new_cost,
            }
            if line.status == 'ok' and line.product_id:
                log_line_vals['old_cost'] = line.product_id.quifa_cost
                log_line_vals['product_id'] = line.product_id.id
            elif line.status == 'ok' and not line.product_id:
                not_found_count += 1
            else:
                error_count += 1
            log_lines_data.append(log_line_vals)

        # Batch write: agrupar productos por nuevo costo y escribir por grupo
        cost_to_ids = {}
        for line in lines_to_update:
            cost_to_ids.setdefault(line.new_cost, []).append(line.product_id.id)

        for new_cost, product_ids in cost_to_ids.items():
            try:
                self.env['price.comparison.product'].browse(product_ids).write(
                    {'quifa_cost': new_cost}
                )
                updated_count += len(product_ids)
            except Exception as exc:
                _logger.error('Error en batch write (costo %s, %d productos): %s',
                              new_cost, len(product_ids), exc)
                error_count += len(product_ids)
                affected_ids = set(product_ids)
                for lv in log_lines_data:
                    if lv.get('product_id') in affected_ids and lv.get('new_cost') == new_cost:
                        lv['status'] = 'error'
                        lv['error_message'] = str(exc)

        # Registrar log
        log_vals['updated'] = updated_count
        log_vals['not_found'] = not_found_count
        log_vals['errors'] = error_count
        log_vals['summary'] = (
            f'Importacion completada\n\n'
            f'Productos actualizados: {updated_count}\n'
            f'Productos no encontrados: {not_found_count}\n'
            f'Errores: {error_count}'
        )

        log = self.env['supplier.cost.import.log'].create(log_vals)
        if log_lines_data:
            log.write({'log_lines': [(0, 0, vals) for vals in log_lines_data]})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Log de importación'),
            'res_model': 'supplier.cost.import.log',
            'res_id': log.id,
            'view_mode': 'form',
            'target': 'current',
        }


class SupplierCostImportWizardLine(models.TransientModel):
    """Líneas de preview del wizard"""
    _name = 'supplier.cost.import.wizard.line'
    _description = 'Línea de Preview de Importación'
    _order = 'row_number'

    wizard_id = fields.Many2one(
        'supplier.cost.import.wizard',
        required=True,
        ondelete='cascade'
    )

    row_number = fields.Integer('Fila', readonly=True)
    barcode = fields.Char('Código de barras', readonly=True)
    product_name = fields.Char('Descripción', readonly=True)

    # Producto encontrado
    product_id = fields.Many2one(
        'price.comparison.product',
        'Producto encontrado',
        readonly=True
    )

    # Valores
    old_cost = fields.Float('Costo anterior', readonly=True, digits=(12, 2))
    new_cost = fields.Float('Costo nuevo', readonly=True, digits=(12, 2))
    cost_change = fields.Float(
        'Cambio',
        compute='_compute_cost_change',
        readonly=True,
        digits=(12, 2)
    )

    # Estado
    status = fields.Selection([
        ('ok', 'Válido'),
        ('not_found', 'Producto no encontrado'),
        ('no_barcode', 'Código de barras inválido'),
        ('invalid_cost', 'Costo inválido'),
        ('error', 'Error de procesamiento'),
    ], 'Estado', readonly=True)

    error_message = fields.Char('Detalles del error', readonly=True)

    @api.depends('old_cost', 'new_cost')
    def _compute_cost_change(self):
        for record in self:
            if record.old_cost:
                record.cost_change = record.new_cost - record.old_cost
            else:
                record.cost_change = record.new_cost if record.new_cost else 0.0
