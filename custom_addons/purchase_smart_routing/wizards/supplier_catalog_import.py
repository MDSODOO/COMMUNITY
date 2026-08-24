import base64
import io
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Patrones conocidos de columnas por nombre de proveedor / layout
COLUMN_PRESETS = {
    'brudifarma': {
        'barcode': 'CODIGO DE BARRAS',
        'price': 'COSTO FACTURA CASA',
        'stock': 'INV',  # match parcial: "INV 13 DE ABR 2026"
        'name': 'NOMBRE COMERCIAL',
        'header_row': 6,
        'sheet': 'INVENTARIO',
        'offer_sheet': 'OFERTA',
        'offer_code_col': 'CODIGO',
        'offer_price_col': 'OFERTA',
        'internal_code': 'CODIGO',
    },
    'quifamesa': {
        'barcode': 'CLAVE',
        'price': 'ULTIMO COSTO',
        'stock': 'EXISTENCIA',
        'name': 'DESCRIPCION',
        'header_row': 1,
        'sheet': 'EXI-PRE',
    },
}


class SupplierCatalogImport(models.TransientModel):
    _name = 'supplier.catalog.import'
    _description = 'Importar Catálogo de Proveedor'

    partner_id = fields.Many2one(
        'res.partner', string='Proveedor', required=True,
        domain=[('supplier_rank', '>', 0)],
    )
    file_data = fields.Binary(string='Archivo Excel', required=True)
    file_name = fields.Char(string='Nombre de Archivo')
    preset = fields.Selection([
        ('brudifarma', 'Brudifarma'),
        ('quifamesa', 'Quifamesa'),
        ('custom', 'Personalizado'),
    ], string='Formato', default='custom', required=True,
        help='Seleccione el formato si es un proveedor conocido, '
             'o "Personalizado" para configurar columnas manualmente.',
    )

    # Campos de mapeo manual (solo si preset = custom)
    col_barcode = fields.Char(
        string='Columna Código de Barras', default='CODIGO DE BARRAS',
    )
    col_price = fields.Char(
        string='Columna Precio', default='PRECIO',
    )
    col_stock = fields.Char(
        string='Columna Stock', default='EXISTENCIA',
    )
    col_name = fields.Char(
        string='Columna Nombre Producto', default='NOMBRE',
    )
    sheet_name = fields.Char(
        string='Nombre de Hoja', default='',
        help='Dejar vacío para usar la primera hoja.',
    )
    header_row = fields.Integer(
        string='Fila de Encabezado (0-indexed)', default=0,
    )

    # Resultados
    result_created = fields.Integer(string='Creados', readonly=True)
    result_updated = fields.Integer(string='Actualizados', readonly=True)
    result_skipped = fields.Integer(string='Sin coincidencia', readonly=True)
    result_log = fields.Text(string='Log de Importación', readonly=True)

    def action_import(self):
        """Importa el catálogo y actualiza product.supplierinfo."""
        self.ensure_one()
        try:
            import openpyxl  # noqa: F401
        except ImportError:
            raise UserError(_(
                'Se requiere la librería openpyxl. '
                'Contacte al administrador del sistema.'
            ))

        import pandas as pd

        file_bytes = base64.b64decode(self.file_data)
        config = self._get_config()

        # ── Leer archivo ─────────────────────────────────────────────
        try:
            df = pd.read_excel(
                io.BytesIO(file_bytes),
                sheet_name=config['sheet'] or 0,
                header=config['header_row'],
            )
        except Exception as e:
            raise UserError(_(
                'Error al leer el archivo Excel: %s', str(e)
            ))

        # ── Mapear columnas ──────────────────────────────────────────
        col_barcode = self._find_column(df, config['barcode'])
        col_price = self._find_column(df, config['price'])
        col_stock = self._find_column(df, config['stock'])

        if not col_barcode:
            raise UserError(_(
                'No se encontró la columna de código de barras "%s" '
                'en las columnas disponibles: %s',
                config['barcode'], ', '.join(df.columns.astype(str)),
            ))
        if not col_price:
            raise UserError(_(
                'No se encontró la columna de precio "%s".', config['price']
            ))

        # ── Normalizar barcodes ──────────────────────────────────────
        df['_barcode'] = (
            df[col_barcode].astype(str)
            .str.strip()
            .str.lstrip('0')
            .str.replace(r'\.0$', '', regex=True)
        )
        df['_price'] = pd.to_numeric(df[col_price], errors='coerce')
        if col_stock:
            df['_stock'] = pd.to_numeric(df[col_stock], errors='coerce').fillna(0)
        else:
            df['_stock'] = 0

        # Filtrar filas válidas
        df = df[
            (df['_barcode'].str.len() > 3)
            & (df['_price'].notna())
            & (df['_price'] > 0)
        ]

        # Agregar duplicados (múltiples lotes): sumar stock, tomar precio mín
        df_agg = df.groupby('_barcode', as_index=False).agg(
            _price=('_price', 'min'),
            _stock=('_stock', 'sum'),
        )

        # ── Cargar ofertas si es Brudifarma ──────────────────────────
        offers = {}
        if config.get('offer_sheet'):
            try:
                df_offer = pd.read_excel(
                    io.BytesIO(file_bytes),
                    sheet_name=config['offer_sheet'],
                    header=0,
                )
                code_col = config.get('offer_code_col', 'CODIGO')
                price_col = config.get('offer_price_col', 'OFERTA')
                if code_col in df_offer.columns and price_col in df_offer.columns:
                    # Necesitamos mapear código interno → barcode
                    internal_code_col = config.get('internal_code', 'CODIGO')
                    if internal_code_col in df.columns:
                        code_to_barcode = dict(zip(
                            df[internal_code_col].astype(str),
                            df['_barcode'],
                        ))
                        for _, row in df_offer.iterrows():
                            code = str(row.get(code_col, ''))
                            price = row.get(price_col)
                            bc = code_to_barcode.get(code)
                            if bc and pd.notna(price) and price > 0:
                                offers[bc] = float(price)
            except Exception:
                _logger.warning('No se pudieron cargar ofertas', exc_info=True)

        # ── Buscar productos por barcode y actualizar supplierinfo ────
        Product = self.env['product.product']
        Supplierinfo = self.env['product.supplierinfo']
        partner = self.partner_id
        today = fields.Date.context_today(self)

        created, updated, skipped = 0, 0, 0
        log_lines = []

        # Pre-cargar todos los productos con barcode
        all_products = Product.search([('barcode', '!=', False)])
        barcode_to_product = {}
        for p in all_products:
            bc = p.barcode.strip().lstrip('0') if p.barcode else ''
            if bc:
                barcode_to_product[bc] = p

        for _, row in df_agg.iterrows():
            barcode = row['_barcode']
            price = float(row['_price'])
            stock = float(row['_stock'])

            product = barcode_to_product.get(barcode)
            if not product:
                skipped += 1
                continue

            # Buscar supplierinfo existente
            existing = Supplierinfo.search([
                ('partner_id', '=', partner.id),
                '|',
                ('product_id', '=', product.id),
                '&',
                ('product_id', '=', False),
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
            ], limit=1)

            offer_price = offers.get(barcode, 0)

            vals = {
                'price': price,
                'supplier_stock': stock,
                'supplier_stock_date': today,
            }
            if offer_price > 0:
                vals['offer_price'] = offer_price

            if existing:
                existing.write(vals)
                updated += 1
            else:
                vals.update({
                    'partner_id': partner.id,
                    'product_tmpl_id': product.product_tmpl_id.id,
                    'product_id': product.id,
                    'min_qty': 0,
                })
                Supplierinfo.create(vals)
                created += 1

        self.result_created = created
        self.result_updated = updated
        self.result_skipped = skipped
        self.result_log = (
            f'Importación completada para {partner.name}:\n'
            f'  • {created} registros creados\n'
            f'  • {updated} registros actualizados\n'
            f'  • {skipped} barcodes sin coincidencia en productos\n'
            f'  • {len(offers)} ofertas aplicadas\n'
            f'  • Total filas procesadas: {len(df_agg)}'
        )

        _logger.info(
            'Catalog import for %s: created=%d, updated=%d, skipped=%d',
            partner.name, created, updated, skipped,
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _get_config(self):
        """Retorna la configuración de columnas según el preset seleccionado."""
        if self.preset in COLUMN_PRESETS:
            return COLUMN_PRESETS[self.preset]
        return {
            'barcode': self.col_barcode or 'CODIGO DE BARRAS',
            'price': self.col_price or 'PRECIO',
            'stock': self.col_stock or 'EXISTENCIA',
            'name': self.col_name or 'NOMBRE',
            'header_row': self.header_row,
            'sheet': self.sheet_name or None,
        }

    @staticmethod
    def _find_column(df, pattern):
        """Busca una columna por nombre exacto o coincidencia parcial."""
        cols = df.columns.astype(str)
        # Exacto
        if pattern in cols:
            return pattern
        # Parcial (case-insensitive)
        pattern_lower = pattern.lower()
        for col in cols:
            if pattern_lower in col.lower():
                return col
        return None
