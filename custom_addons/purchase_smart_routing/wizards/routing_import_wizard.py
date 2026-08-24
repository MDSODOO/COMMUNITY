import base64
import io
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RoutingImportWizard(models.TransientModel):
    _name = 'purchase.routing.import.wizard'
    _description = 'Importar Demanda de Reabastecimiento'

    routing_id = fields.Many2one(
        'purchase.routing', string='Routing', required=True,
    )
    file_data = fields.Binary(string='Archivo Excel', required=True)
    file_name = fields.Char(string='Nombre de Archivo')

    # Configuración de columnas
    col_barcode = fields.Char(
        string='Columna Código de Barras',
        default='Código de barras',
    )
    col_qty = fields.Char(
        string='Columna Cantidad',
        default='Por ordenar',
    )
    col_brand = fields.Char(
        string='Columna Línea/Marca',
        default='Línea',
    )
    header_row = fields.Integer(
        string='Fila de Encabezado (0-indexed)', default=0,
    )

    # Resultados
    result_imported = fields.Integer(readonly=True)
    result_skipped = fields.Integer(readonly=True)
    result_log = fields.Text(readonly=True)

    def action_import(self):
        """Importa las líneas de demanda al routing."""
        self.ensure_one()
        import pandas as pd

        file_bytes = base64.b64decode(self.file_data)

        try:
            df = pd.read_excel(
                io.BytesIO(file_bytes),
                header=self.header_row,
            )
        except Exception as e:
            raise UserError(_(
                'Error al leer el archivo: %s', str(e)
            ))

        # Validar columnas
        col_bc = self._find_col(df, self.col_barcode)
        col_qty = self._find_col(df, self.col_qty)
        col_brand = self._find_col(df, self.col_brand)

        if not col_bc:
            raise UserError(_(
                'Columna de barcode "%s" no encontrada. '
                'Columnas disponibles: %s',
                self.col_barcode, ', '.join(df.columns.astype(str)),
            ))
        if not col_qty:
            raise UserError(_(
                'Columna de cantidad "%s" no encontrada.', self.col_qty
            ))

        # Filtrar filas con demanda > 0
        df[col_qty] = pd.to_numeric(df[col_qty], errors='coerce')
        df = df[df[col_qty].notna() & (df[col_qty] > 0)].copy()

        if df.empty:
            raise UserError(_(
                'No se encontraron filas con demanda mayor a 0.'
            ))

        # Normalizar barcodes
        df['_barcode'] = (
            df[col_bc].astype(str)
            .str.strip()
            .str.lstrip('0')
            .str.replace(r'\.0$', '', regex=True)
        )

        # Pre-cargar productos
        Product = self.env['product.product']
        all_products = Product.search([('barcode', '!=', False)])
        barcode_map = {}
        for p in all_products:
            bc = p.barcode.strip().lstrip('0') if p.barcode else ''
            if bc:
                barcode_map[bc] = p

        imported, skipped = 0, 0
        line_vals_list = []

        for _, row in df.iterrows():
            barcode = row['_barcode']
            qty = float(row[col_qty])
            brand = str(row.get(col_brand, '')) if col_brand else ''

            product = barcode_map.get(barcode)
            if not product:
                skipped += 1
                continue

            line_vals_list.append({
                'routing_id': self.routing_id.id,
                'product_id': product.id,
                'qty_demanded': qty,
                'line_brand': brand if brand and brand != 'nan' else '',
            })
            imported += 1

        if line_vals_list:
            self.env['purchase.routing.line'].create(line_vals_list)

        self.result_imported = imported
        self.result_skipped = skipped
        self.result_log = (
            f'Importación de demanda completada:\n'
            f'  • {imported} productos importados\n'
            f'  • {skipped} barcodes sin coincidencia\n'
            f'  • Total filas con demanda: {len(df)}'
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @staticmethod
    def _find_col(df, pattern):
        if not pattern:
            return None
        cols = df.columns.astype(str)
        if pattern in cols:
            return pattern
        pattern_lower = pattern.lower()
        for col in cols:
            if pattern_lower in col.lower():
                return col
        return None
