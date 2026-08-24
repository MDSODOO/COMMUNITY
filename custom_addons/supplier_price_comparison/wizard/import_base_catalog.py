# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, _
from odoo.exceptions import UserError

from ..services.excel_utils import col_index, normalize_barcode, parse_number, read_excel

_logger = logging.getLogger(__name__)


class ImportBaseCatalog(models.TransientModel):
    _name = 'import.base.catalog'
    _description = 'Importar Catálogo Base Quifamesa'

    file = fields.Binary('Archivo Excel', required=True)
    filename = fields.Char('Nombre del Archivo')
    header_row = fields.Integer(
        'Fila de Encabezados', default=1,
        help='Número de fila donde están los encabezados (1 = primera fila)')
    col_barcode = fields.Char(
        'Columna Código de Barras', default='A', required=True,
        help='Letra de columna (A, B, C...) o nombre del encabezado')
    col_name = fields.Char(
        'Columna Nombre Producto', default='C', required=True)
    col_brand = fields.Char(
        'Columna Marca/Laboratorio', default='D',
        help='Dejar vacío si no aplica')
    col_cost = fields.Char(
        'Columna Costo Quifamesa', default='H', required=True)
    sheet_name = fields.Char(
        'Primera Hoja', help='El sistema usa siempre la primera hoja del archivo')
    mode = fields.Selection([
        ('create', 'Crear nuevos (ignorar existentes)'),
        ('update', 'Actualizar existentes y crear nuevos'),
        ('replace', 'Reemplazar todo (borrar y crear)'),
    ], string='Modo de Importación', default='update', required=True)
    result_message = fields.Text('Resultado', readonly=True)

    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_('Seleccione un archivo Excel.'))

        rows = read_excel(self.file, self.filename, self.sheet_name)
        if not rows:
            raise UserError(_('El archivo está vacío.'))

        header_idx = self.header_row - 1
        if header_idx >= len(rows):
            raise UserError(_('La fila de encabezados excede el total de filas.'))

        headers = rows[header_idx]
        idx_bc = col_index(self.col_barcode, headers)
        idx_name = col_index(self.col_name, headers)
        idx_brand = col_index(self.col_brand, headers) if self.col_brand else None
        idx_cost = col_index(self.col_cost, headers)

        Product = self.env['price.comparison.product']

        if self.mode == 'replace':
            Product.search([]).unlink()

        existing = {p.barcode: p for p in Product.search([])}
        created = updated = skipped = 0
        errors = []

        # Acumula nuevos productos para batch create al final del loop
        pending_vals = {}   # bc → vals dict (deduplicado por barcode)

        for i, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
            try:
                bc_raw = row[idx_bc] if idx_bc < len(row) else None
                bc = normalize_barcode(bc_raw)
                if not bc:
                    continue

                name_raw = row[idx_name] if idx_name < len(row) else ''
                name = str(name_raw).strip() if name_raw else ''
                if not name:
                    continue

                brand = ''
                if idx_brand is not None and idx_brand < len(row) and row[idx_brand]:
                    brand = str(row[idx_brand]).strip()

                cost = 0.0
                cost_raw = row[idx_cost] if idx_cost < len(row) else None
                if cost_raw:
                    # parse_number tolera formato de moneda MX ("$1,234.50")
                    cost = parse_number(cost_raw) or 0.0

                if bc in existing:
                    if self.mode in ('update', 'replace'):
                        vals = {'name': name, 'quifa_cost': cost}
                        if brand:
                            vals['brand'] = brand
                        existing[bc].write(vals)
                        updated += 1
                    else:
                        skipped += 1
                elif bc in pending_vals:
                    # Barcode duplicado en el Excel — actualizar vals pendientes
                    pending_vals[bc].update({'name': name, 'quifa_cost': cost})
                    if brand:
                        pending_vals[bc]['brand'] = brand
                else:
                    pending_vals[bc] = {
                        'barcode': bc,
                        'name': name,
                        'brand': brand,
                        'quifa_cost': cost,
                    }
                    created += 1

            except UserError:
                raise
            except Exception as e:
                errors.append(f'Fila {i}: {e}')
                if len(errors) > 20:
                    errors.append('... (más errores omitidos)')
                    break

        # Batch create — 1 INSERT en lugar de N
        if pending_vals:
            new_products = Product.create(list(pending_vals.values()))
            for prod in new_products:
                existing[prod.barcode] = prod

        # Guarda: si no se procesó ningún producto, el mapeo de columnas es erróneo
        if not (created or updated or skipped):
            raise UserError(_(
                'No se importó ningún producto. Verifique el mapeo de columnas:\n'
                '- Código de Barras debe apuntar a la columna con códigos numéricos.\n'
                '- Nombre debe apuntar a la columna con la descripción del producto.\n'
                '- Fila de Encabezados debe coincidir con la fila de títulos.\n\n'
                'Encabezados detectados: %s'
            ) % ', '.join(str(h) for h in headers if h))

        msg = (
            f'Importación completada\n\n'
            f'Creados: {created}\n'
            f'Actualizados: {updated}\n'
            f'Omitidos: {skipped}\n'
        )
        if errors:
            msg += f'\nErrores ({len(errors)}):\n' + '\n'.join(errors[:10])

        self.result_message = msg

        # Redirigir a la lista de productos base
        return {
            'type': 'ir.actions.act_window',
            'name': _('Productos Base'),
            'res_model': 'price.comparison.product',
            'view_mode': 'list,form',
            'target': 'current',
        }
