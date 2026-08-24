# -*- coding: utf-8 -*-
import logging
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.excel_utils import col_index, normalize_barcode, parse_number, read_excel

_logger = logging.getLogger(__name__)


class ImportSupplierCatalog(models.TransientModel):
    _name = 'import.supplier.catalog'
    _description = 'Importar Catálogo de Proveedor'

    supplier_id = fields.Many2one(
        'res.partner', string='Proveedor', required=True,
        help='Seleccione el proveedor al que corresponde este catálogo')
    file = fields.Binary('Archivo Excel', required=True)
    filename = fields.Char('Nombre del Archivo')
    header_row = fields.Integer(
        'Fila de Encabezados', default=1,
        help='Número de fila donde están los encabezados (1 = primera fila)')
    col_barcode = fields.Char(
        'Columna Código de Barras', default='A', required=True,
        help='Letra de columna (A, B, C...) o nombre del encabezado')
    col_price = fields.Char(
        'Columna Precio', default='B', required=True,
        help='Letra de columna o nombre del encabezado con el precio a usar')
    col_name = fields.Char(
        'Columna Nombre Producto',
        help='Letra o nombre del encabezado. Se usa para crear productos '
             'que no existan en el catálogo base.')
    col_qty = fields.Char(
        'Columna A la mano',
        help='Columna con la cantidad A la mano del proveedor (opcional)')
    col_lead_time = fields.Char(
        'Columna Días de Entrega',
        help='Columna con los días de entrega del proveedor (opcional)')
    sheet_name = fields.Char(
        'Primera Hoja',
        help='El sistema usa siempre la primera hoja del archivo')
    strip_barcode_zeros = fields.Boolean(
        'Quitar ceros a la izquierda del código de barras',
        help='Activar para proveedores como Brudifarma que agregan ceros al inicio')
    create_missing = fields.Boolean(
        'Crear productos faltantes',
        default=True,
        help='Si el código de barras no existe en el catálogo base, '
             'crear el producto automáticamente')
    catalog_label = fields.Char(
        'Etiqueta del Catálogo',
        help='Nombre descriptivo para identificar la fuente (ej: "A la mano BF", "Elite HS")')
    mode = fields.Selection([
        ('update', 'Actualizar precios existentes y agregar nuevos'),
        ('replace', 'Reemplazar todos los precios de este proveedor'),
    ], string='Modo', default='update', required=True)
    result_message = fields.Text('Resultado', readonly=True)

    @api.onchange('supplier_id')
    def _onchange_supplier_id(self):
        if self.supplier_id and not self.catalog_label:
            self.catalog_label = self.supplier_id.name

    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_('Seleccione un archivo Excel.'))

        # Step 29: bloquear importación para proveedores inactivos
        if not self.supplier_id.active:
            raise UserError(_(
                'El proveedor "%s" está inactivo en Odoo. '
                'Reactívelo antes de cargar su catálogo.'
            ) % self.supplier_id.name)

        rows = read_excel(self.file, self.filename, self.sheet_name)
        if not rows:
            raise UserError(_('El archivo está vacío.'))

        header_idx = self.header_row - 1
        if header_idx >= len(rows):
            raise UserError(_('La fila de encabezados excede el total de filas.'))

        headers = rows[header_idx]
        idx_bc = col_index(self.col_barcode, headers)
        idx_price = col_index(self.col_price, headers)
        idx_name = col_index(self.col_name, headers) if self.col_name else None
        idx_qty = col_index(self.col_qty, headers) if self.col_qty else None
        idx_lead = col_index(self.col_lead_time, headers) if self.col_lead_time else None

        Product = self.env['price.comparison.product']
        Line = self.env['price.comparison.line']

        # Construir lookup tolerante: barcode crudo + versión normalizada +
        # versión sin ceros. Los catálogos viejos cargados por el importador
        # nativo de Odoo guardan barcodes con basura (punto final "7502...831.",
        # espacios, ceros). normalize_barcode los limpia igual que a las filas
        # entrantes, así que un código limpio del proveedor encuentra al producto
        # legado SIN crear un duplicado.
        all_products = Product.search([])
        bc_map = {}
        for p in all_products:
            if not p.barcode:
                continue
            bc_map.setdefault(p.barcode, p)
            norm = normalize_barcode(p.barcode)
            if norm:
                bc_map.setdefault(norm, p)
                norm_stripped = norm.lstrip('0')
                if norm_stripped:
                    bc_map.setdefault(norm_stripped, p)
            stripped = p.barcode.lstrip('0')
            if stripped:
                bc_map.setdefault(stripped, p)

        # Step 20: SQL DELETE directo para replace — más eficiente que ORM unlink()
        if self.mode == 'replace':
            affected_product_ids = [
                line.product_id.id for line in
                Line.search([('supplier_id', '=', self.supplier_id.id)])
            ]
            self.env.cr.execute(
                "DELETE FROM price_comparison_line WHERE supplier_id = %s",
                [self.supplier_id.id]
            )
            self.env.invalidate_all()
            # Forzar recomputo de best_price/supplier_count en productos afectados
            if affected_product_ids:
                Product.browse(affected_product_ids)._compute_best_price()
                Product.browse(affected_product_ids)._compute_supplier_count()

        # update: cargar líneas existentes (keyed por barcode del producto)
        existing_lines = {}
        if self.mode == 'update':
            for line in Line.search([('supplier_id', '=', self.supplier_id.id)]):
                existing_lines[line.barcode] = line

        created = updated = not_found = auto_created = bad_price = 0
        catalog_label = self.catalog_label or self.supplier_id.name
        today = fields.Date.today()
        strip = self.strip_barcode_zeros

        new_lines_vals = []
        price_updates = {}      # {line_id: new_price}
        seen_barcodes = set()
        affected_product_ids = set()

        for row in rows[header_idx + 1:]:
            try:
                bc_raw = row[idx_bc] if idx_bc < len(row) else None
                bc = normalize_barcode(bc_raw, strip_zeros=strip)
                if not bc:
                    continue

                price_raw = row[idx_price] if idx_price < len(row) else None
                if price_raw is None or price_raw == '':
                    continue
                # parse_number tolera formato de moneda MX ("$1,234.50", "1234,50")
                # que float() rechazaría, descartando la fila en silencio.
                price = parse_number(price_raw)
                if price is None:
                    bad_price += 1
                    continue
                if price <= 0:
                    continue

                if bc in seen_barcodes:
                    continue
                seen_barcodes.add(bc)

                # Extraer campos opcionales
                qty_on_hand = 0.0
                if idx_qty is not None and idx_qty < len(row) and row[idx_qty]:
                    qty_on_hand = parse_number(row[idx_qty]) or 0.0

                lead_time = 0
                if idx_lead is not None and idx_lead < len(row) and row[idx_lead]:
                    lead_parsed = parse_number(row[idx_lead])
                    if lead_parsed is not None:
                        lead_time = int(lead_parsed)

                # Resolver producto
                product = bc_map.get(bc)
                if not product and self.create_missing:
                    prod_name = ''
                    if idx_name is not None and idx_name < len(row) and row[idx_name]:
                        prod_name = str(row[idx_name]).strip()
                    if not prod_name:
                        prod_name = f'Producto {bc}'

                    store_bc = bc
                    if strip and bc_raw:
                        store_bc = normalize_barcode(bc_raw, strip_zeros=False) or bc

                    product = Product.create({'barcode': store_bc, 'name': prod_name})
                    bc_map[store_bc] = product
                    bc_map[bc] = product
                    auto_created += 1
                elif not product:
                    not_found += 1
                    continue

                affected_product_ids.add(product.id)
                orig_bc = product.barcode

                if orig_bc in existing_lines:
                    price_updates[existing_lines[orig_bc].id] = (
                        price, qty_on_hand, lead_time
                    )
                    updated += 1
                else:
                    new_lines_vals.append({
                        'product_id': product.id,
                        'supplier_id': self.supplier_id.id,
                        'price': price,
                        'supplier_qty_on_hand': qty_on_hand,
                        'lead_time': lead_time,
                        'import_date': today,
                        'catalog_name': catalog_label,
                    })
                    created += 1

            except UserError:
                raise
            except Exception as e:
                _logger.warning('Import supplier row error: %s', e)
                continue

        # Step 21: diferir recomputo — crear/actualizar en bloque y recalcular al final
        # Batch create nuevas líneas
        if new_lines_vals:
            Line.with_context(import_no_history=True).create(new_lines_vals)

        # Batch update: agrupar por (price, qty, lead_time) para minimizar writes ORM
        if price_updates:
            group_map = defaultdict(list)
            for line_id, vals_tuple in price_updates.items():
                group_map[vals_tuple].append(line_id)

            for (price, qty, lead), line_ids in group_map.items():
                Line.browse(line_ids).with_context(import_no_history=True).write({
                    'price': price,
                    'supplier_qty_on_hand': qty,
                    'lead_time': lead,
                    'import_date': today,
                    'catalog_name': catalog_label,
                })

        # Step 21: recomputo final único para todos los productos afectados
        if affected_product_ids:
            affected_products = Product.browse(list(affected_product_ids))
            affected_products._compute_best_price()
            affected_products._compute_supplier_count()

        # Guarda: si no se procesó ninguna línea, el mapeo de columnas es erróneo
        if not (created or updated or not_found or auto_created):
            extra = ''
            if bad_price:
                extra = _(
                    '\n\nNOTA: %s filas tenían un precio que no se pudo '
                    'interpretar como número. Verifique que la columna de '
                    'Precio apunte a los precios y no a texto.'
                ) % bad_price
            raise UserError(_(
                'No se importó ningún precio. Verifique el mapeo de columnas:\n'
                '- Código de Barras debe apuntar a la columna con códigos numéricos.\n'
                '- Precio debe apuntar a la columna con el precio del proveedor.\n'
                '- Fila de Encabezados debe coincidir con la fila de títulos.\n\n'
                'Encabezados detectados: %s'
            ) % ', '.join(str(h) for h in headers if h) + extra)

        msg = (
            f'Importacion de {catalog_label} completada\n\n'
            f'Proveedor: {self.supplier_id.name}\n'
            f'Precios creados: {created}\n'
            f'Precios actualizados: {updated}\n'
            f'Productos nuevos (auto-creados): {auto_created}\n'
            f'No encontrados (sin crear): {not_found}\n'
            f'Filas con precio ilegible: {bad_price}\n'
        )
        self.result_message = msg

        return {
            'type': 'ir.actions.act_window',
            'name': _('Comparador de Precios'),
            'res_model': 'price.comparison.line',
            'view_mode': 'pivot,list',
            'target': 'current',
        }
