"""
Wizard: Comparador de Catálogos A/B con fuzzy matching y regla del 6%.

Flujo:
  1. El usuario configura los proveedores A (preferido) y B (alternativo)
     y sube sus catálogos Excel.
  2. Vista previa: se muestran estadísticas de coincidencia (matched / unmatched).
  3. Aplicar: actualiza product.supplierinfo, marca Proveedor A como preferido
     en las líneas y recalcula el routing.
  4. Los artículos sin coincidencia se registran en el chatter de la sesión.

Estrategia de matching (en orden):
  1. Exacto por default_code  ↔  columna SKU/código del catálogo.
  2. Exacto por barcode        ↔  columna SKU/código del catálogo.
  3. Fuzzy por nombre          ↔  columna descripción del catálogo (threshold 0.70).
"""
from __future__ import annotations

import base64
import io
import logging
import warnings
from difflib import SequenceMatcher, get_close_matches
from typing import Optional

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    openpyxl = None


# ── Constantes de columnas ────────────────────────────────────────────────────

_SKU_ALIASES = {
    'sku', 'codigo', 'code', 'referencia', 'referencia_interna',
    'default_code', 'clave', 'articulo', 'cve',
}
_DESC_ALIASES = {
    'descripcion', 'description', 'nombre', 'name', 'producto',
    'descripción', 'desc', 'articulo', 'detalle',
}
_PRICE_ALIASES = {
    'precio', 'price', 'costo', 'cost', 'precio_unitario',
    'unit_price', 'importe', 'ultimo_costo',
}
_STOCK_ALIASES = {
    'stock', 'existencia', 'disponible', 'inventory',
    'stock_disponible', 'cantidad', 'qty', 'a la mano',
}

FUZZY_THRESHOLD = 0.70   # umbral mínimo de similitud para considerar coincidencia


# ── Helpers de matching ──────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Normaliza un texto para comparaciones: upper, sin espacios dobles."""
    return ' '.join(str(text).upper().split())


def _find_col(df_columns: list[str], aliases: set[str]) -> Optional[str]:
    """Busca la primera columna que coincida con algún alias (exacto o parcial)."""
    cols_lower = [c.lower().strip() for c in df_columns]
    for col, col_low in zip(df_columns, cols_lower):
        if col_low in aliases:
            return col
    for col, col_low in zip(df_columns, cols_lower):
        if any(alias in col_low for alias in aliases):
            return col
    return None


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


# ── Modelo TransientModel ────────────────────────────────────────────────────

class RoutingCatalogCompare(models.TransientModel):
    _name = 'routing.catalog.compare'
    _description = 'Comparar Catálogos de Proveedores A y B'

    # ── Sesión de routing destino ─────────────────────────────────────
    routing_id = fields.Many2one(
        'purchase.routing', string='Sesión de Routing',
        required=True, ondelete='cascade',
    )

    # ── Proveedor A — preferido/principal ────────────────────────────
    partner_a_id = fields.Many2one(
        'res.partner', string='Proveedor A (Preferido)',
        required=True, domain=[('supplier_rank', '>', 0)],
    )
    catalog_a_file = fields.Binary(
        string='Catálogo Proveedor A (.xlsx)', required=True,
    )
    catalog_a_filename = fields.Char()

    # ── Proveedor B — alternativo ─────────────────────────────────────
    partner_b_id = fields.Many2one(
        'res.partner', string='Proveedor B (Alternativo)',
        required=True, domain=[('supplier_rank', '>', 0)],
    )
    catalog_b_file = fields.Binary(
        string='Catálogo Proveedor B (.xlsx)', required=True,
    )
    catalog_b_filename = fields.Char()

    # ── Configuración de columnas (flexible) ─────────────────────────
    col_sku = fields.Char(
        string='Columna SKU / Código', default='SKU',
        help='Nombre de la columna con el código de producto en los catálogos Excel.',
    )
    col_desc = fields.Char(
        string='Columna Descripción', default='Descripcion',
        help='Nombre de la columna con la descripción/nombre del producto.',
    )
    col_price = fields.Char(
        string='Columna Precio', default='Precio',
    )
    col_stock = fields.Char(
        string='Columna Stock', default='Stock',
    )
    header_row = fields.Integer(
        string='Fila de Encabezado (0-indexed)', default=0,
    )

    # ── Umbral de precio ──────────────────────────────────────────────
    threshold_percent = fields.Float(
        string='Umbral A→B (%)',
        default=lambda self: self._default_threshold(),
        digits=(5, 2),
        help=(
            'Solo se selecciona el Proveedor B si su precio es al menos N%% más barato que A.\n'
            'Fórmula: precio_B <= precio_A × (1 - N/100)\n'
            'Ejemplo con 6%%: se usa B solo si precio_B ≤ precio_A × 0.94'
        ),
    )

    # ── Estado y estadísticas ─────────────────────────────────────────
    state = fields.Selection([
        ('config', 'Configurar'),
        ('preview', 'Vista Previa'),
        ('done', 'Completado'),
    ], default='config')

    lines_total = fields.Integer(string='Líneas en routing', readonly=True)
    matched_a = fields.Integer(string='Coincidencias en A', readonly=True)
    matched_b = fields.Integer(string='Coincidencias en B', readonly=True)
    unmatched_count = fields.Integer(string='Sin coincidencia', readonly=True)
    assigned_a = fields.Integer(string='Asignados a A', readonly=True)
    assigned_b = fields.Integer(string='Asignados a B', readonly=True)
    result_html = fields.Html(string='Resumen', readonly=True)
    unmatched_detail = fields.Text(
        string='Artículos sin coincidencia', readonly=True,
    )

    # ── Defaults ─────────────────────────────────────────────────────
    def _default_threshold(self):
        return float(
            self.env['ir.config_parameter'].sudo().get_param(
                'purchase_smart_routing.threshold_percent', '6.0'
            )
        )

    # ── Validaciones ─────────────────────────────────────────────────
    @api.constrains('partner_a_id', 'partner_b_id')
    def _check_partners_different(self):
        for rec in self:
            if rec.partner_a_id and rec.partner_b_id and rec.partner_a_id == rec.partner_b_id:
                raise ValidationError(
                    _('El Proveedor A y el Proveedor B deben ser diferentes.')
                )

    @api.constrains('threshold_percent')
    def _check_threshold(self):
        for rec in self:
            if not (0.0 <= rec.threshold_percent <= 100.0):
                raise ValidationError(
                    _('El umbral debe estar entre 0%% y 100%%.')
                )

    # ── Lectura de Excel ─────────────────────────────────────────────
    def _read_catalog(self, file_binary: bytes, filename: str) -> dict:
        """
        Lee un archivo Excel y retorna un dict:
          { normalized_sku: {'sku': str, 'desc': str, 'price': float, 'stock': float} }

        La clave es el SKU normalizado (upper, sin espacios). Además construye
        un índice de descripciones normalizadas para fuzzy matching.

        Returns:
            {
              'by_sku':  { sku_normalized: row_dict },
              'by_desc': { desc_normalized: row_dict },
              'names':   [ desc_normalized, ... ]   # para get_close_matches
            }
        """
        if not openpyxl:
            raise UserError(_(
                "La librería 'openpyxl' no está instalada en el servidor.\n"
                "Agrégala al archivo requirements.txt del repositorio."
            ))

        try:
            raw = base64.b64decode(file_binary)
            buf = io.BytesIO(raw)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                wb = openpyxl.load_workbook(buf, data_only=True, read_only=True)
            ws = wb.active
            rows = list(ws.values)
            wb.close()
        except Exception as e:
            raise UserError(_(
                "No se pudo abrir '%(f)s': %(e)s", f=filename, e=str(e)
            ))

        if not rows or len(rows) <= self.header_row:
            raise UserError(_(
                "'%(f)s' no tiene datos suficientes (fila de encabezado: %(r)s).",
                f=filename, r=self.header_row,
            ))

        # Encabezados
        header_idx = self.header_row
        headers = [
            str(h).strip() if h is not None else f"Col_{i}"
            for i, h in enumerate(rows[header_idx])
        ]
        data_rows = rows[header_idx + 1:]

        # Detectar columnas
        sku_col = self._detect_col(headers, self.col_sku, _SKU_ALIASES, filename, required=False)
        desc_col = self._detect_col(headers, self.col_desc, _DESC_ALIASES, filename, required=False)
        price_col = self._detect_col(headers, self.col_price, _PRICE_ALIASES, filename, required=True)
        stock_col = self._detect_col(headers, self.col_stock, _STOCK_ALIASES, filename, required=False)

        by_sku = {}
        by_desc = {}
        names = []

        for row in data_rows:
            row_dict = dict(zip(headers, row))

            raw_price = row_dict.get(price_col)
            try:
                price = float(raw_price) if raw_price is not None else 0.0
            except (TypeError, ValueError):
                price = 0.0
            if price <= 0:
                continue

            raw_stock = row_dict.get(stock_col) if stock_col else None
            try:
                stock = float(raw_stock) if raw_stock is not None else 0.0
            except (TypeError, ValueError):
                stock = 0.0

            sku_raw = str(row_dict.get(sku_col, '') or '').strip() if sku_col else ''
            desc_raw = str(row_dict.get(desc_col, '') or '').strip() if desc_col else ''

            entry = {
                'sku': sku_raw,
                'desc': desc_raw,
                'price': price,
                'stock': stock,
            }

            sku_norm = _normalize(sku_raw) if sku_raw else None
            desc_norm = _normalize(desc_raw) if desc_raw else None

            if sku_norm:
                by_sku[sku_norm] = entry
            if desc_norm:
                by_desc[desc_norm] = entry
                names.append(desc_norm)

        return {'by_sku': by_sku, 'by_desc': by_desc, 'names': names}

    def _detect_col(
        self, headers: list[str], configured: str,
        aliases: set[str], filename: str, required: bool = True,
    ) -> Optional[str]:
        """Busca la columna configurada; si no existe, intenta aliases."""
        # Exacto con el valor configurado
        if configured and configured in headers:
            return configured
        # Parcial con el valor configurado
        if configured:
            conf_low = configured.lower()
            for h in headers:
                if conf_low in h.lower():
                    return h
        # Aliases
        col = _find_col(headers, aliases)
        if col:
            return col
        if required:
            raise UserError(_(
                "'%(f)s': no se encontró columna de precio.\n"
                "Columnas disponibles: %(cols)s",
                f=filename, cols=', '.join(headers),
            ))
        return None

    # ── Matching de producto Odoo ↔ entrada de catálogo ──────────────
    def _find_in_catalog(self, product, catalog: dict) -> Optional[dict]:
        """
        Busca un producto de Odoo en un catálogo.
        Estrategia (en orden de precisión):
          1. default_code exacto ↔ catalog SKU
          2. barcode exacto      ↔ catalog SKU
          3. nombre fuzzy        ↔ catalog descripción (threshold 0.70)
        """
        by_sku = catalog['by_sku']
        by_desc = catalog['by_desc']
        names = catalog['names']

        # 1. Exacto por default_code
        if product.default_code:
            key = _normalize(product.default_code)
            if key in by_sku:
                return by_sku[key]

        # 2. Exacto por barcode
        if product.barcode:
            key = _normalize(product.barcode)
            if key in by_sku:
                return by_sku[key]

        # 3. Fuzzy por nombre del producto contra descripciones del catálogo
        if product.name and names:
            query = _normalize(product.name)
            matches = get_close_matches(query, names, n=1, cutoff=FUZZY_THRESHOLD)
            if matches:
                return by_desc[matches[0]]

        return None

    # ── Paso 1: Vista previa ──────────────────────────────────────────
    def action_preview(self):
        """Lee catálogos, realiza matching y muestra estadísticas sin modificar datos."""
        self.ensure_one()
        routing = self.routing_id
        if not routing.line_ids:
            raise UserError(_(
                'La sesión de routing no tiene líneas de demanda.\n'
                'Importe la demanda primero (desde Excel o desde Órdenes de Compra).'
            ))

        catalog_a = self._read_catalog(self.catalog_a_file, self.catalog_a_filename or 'A.xlsx')
        catalog_b = self._read_catalog(self.catalog_b_file, self.catalog_b_filename or 'B.xlsx')

        matched_a = 0
        matched_b = 0
        unmatched = []
        preview_assigned_a = 0
        preview_assigned_b = 0
        threshold = self.threshold_percent / 100.0

        for line in routing.line_ids:
            entry_a = self._find_in_catalog(line.product_id, catalog_a)
            entry_b = self._find_in_catalog(line.product_id, catalog_b)

            if entry_a:
                matched_a += 1
            if entry_b:
                matched_b += 1
            if not entry_a and not entry_b:
                unmatched.append(line.product_id.display_name)
                continue

            # Simular asignación para las estadísticas de preview
            price_a = entry_a['price'] if entry_a else None
            price_b = entry_b['price'] if entry_b else None

            winner = self._apply_threshold_rule(price_a, price_b, threshold)
            if winner == 'a':
                preview_assigned_a += 1
            else:
                preview_assigned_b += 1

        self.write({
            'state': 'preview',
            'lines_total': len(routing.line_ids),
            'matched_a': matched_a,
            'matched_b': matched_b,
            'unmatched_count': len(unmatched),
            'assigned_a': preview_assigned_a,
            'assigned_b': preview_assigned_b,
            'unmatched_detail': '\n'.join(unmatched) if unmatched else False,
        })
        return self._reopen()

    # ── Paso 2: Aplicar ───────────────────────────────────────────────
    def action_apply(self):
        """
        Aplica los catálogos:
          1. Actualiza product.supplierinfo para A y B.
          2. Auto-asigna default_code si el producto no tiene SKU.
          3. Marca source_partner_id = A en todas las líneas.
          4. Recalcula el routing con el umbral configurado.
          5. Registra artículos no encontrados en el chatter.
        """
        self.ensure_one()
        routing = self.routing_id
        if not routing.line_ids:
            raise UserError(_('No hay líneas de demanda en la sesión de routing.'))

        catalog_a = self._read_catalog(self.catalog_a_file, self.catalog_a_filename or 'A.xlsx')
        catalog_b = self._read_catalog(self.catalog_b_file, self.catalog_b_filename or 'B.xlsx')

        threshold = self.threshold_percent / 100.0
        today = fields.Date.context_today(self)

        unmatched = []
        stats = {'a': 0, 'b': 0, 'both': 0, 'none': 0, 'skus_auto': 0}

        for line in routing.line_ids:
            product = line.product_id
            entry_a = self._find_in_catalog(product, catalog_a)
            entry_b = self._find_in_catalog(product, catalog_b)

            # Auto-asignar default_code si el producto no tiene SKU
            if not product.default_code:
                catalog_sku = (entry_a or entry_b or {}).get('sku')
                if catalog_sku:
                    product.sudo().write({'default_code': catalog_sku})
                    stats['skus_auto'] += 1
                    _logger.info(
                        'Auto-SKU: producto %s → default_code=%s', product.id, catalog_sku
                    )

            if not entry_a and not entry_b:
                stats['none'] += 1
                unmatched.append(f'• {product.display_name}')
                continue

            if entry_a and entry_b:
                stats['both'] += 1
            elif entry_a:
                stats['a'] += 1
            else:
                stats['b'] += 1

            # Actualizar product.supplierinfo para los proveedores encontrados
            if entry_a:
                self._upsert_supplierinfo(product, self.partner_a_id, entry_a, today)
            if entry_b:
                self._upsert_supplierinfo(product, self.partner_b_id, entry_b, today)

            # Marcar A como proveedor preferido en la línea (para la lógica de umbral del motor)
            line.source_partner_id = self.partner_a_id

        # Actualizar umbral en la sesión y recalcular
        routing.threshold_percent = self.threshold_percent
        routing.action_calculate()

        # Registrar excepciones en el chatter
        self._post_chatter_report(routing, unmatched, stats)

        # Construir resumen HTML
        result_html = self._build_result_html(routing, unmatched, stats, threshold)

        self.write({
            'state': 'done',
            'lines_total': len(routing.line_ids),
            'matched_a': stats['a'] + stats['both'],
            'matched_b': stats['b'] + stats['both'],
            'unmatched_count': stats['none'],
            'assigned_a': len(routing.line_ids.filtered(
                lambda l: l.winner_partner_id == self.partner_a_id
            )),
            'assigned_b': len(routing.line_ids.filtered(
                lambda l: l.winner_partner_id == self.partner_b_id
            )),
            'result_html': result_html,
            'unmatched_detail': '\n'.join(unmatched) if unmatched else False,
        })
        return self._reopen()

    # ── Helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _apply_threshold_rule(
        price_a: Optional[float],
        price_b: Optional[float],
        threshold: float,
    ) -> str:
        """
        Aplica la regla de preferencia A con umbral.
        Retorna 'a' o 'b'.
        Lógica: usar B solo si precio_B <= precio_A * (1 - threshold).
        """
        if price_a and not price_b:
            return 'a'
        if price_b and not price_a:
            return 'b'
        if price_a and price_b:
            if price_b <= price_a * (1.0 - threshold):
                return 'b'
        return 'a'

    def _upsert_supplierinfo(self, product, partner, entry: dict, today):
        """Crea o actualiza product.supplierinfo para el par (product, partner)."""
        Supplierinfo = self.env['product.supplierinfo']
        existing = Supplierinfo.search([
            ('partner_id', '=', partner.id),
            '|',
            ('product_id', '=', product.id),
            '&', ('product_id', '=', False),
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
        ], limit=1)

        vals = {
            'price': entry['price'],
            'supplier_stock': entry['stock'],
            'supplier_stock_date': today,
        }
        if existing:
            existing.write(vals)
        else:
            vals.update({
                'partner_id': partner.id,
                'product_tmpl_id': product.product_tmpl_id.id,
                'product_id': product.id,
                'min_qty': 0.0,
            })
            Supplierinfo.create(vals)

    def _post_chatter_report(self, routing, unmatched: list, stats: dict):
        """Publica un mensaje en el chatter de la sesión con el reporte de excepciones."""
        lines = [
            f'<b>Comparación de catálogos: {self.partner_a_id.name} (A) vs '
            f'{self.partner_b_id.name} (B) — umbral {self.threshold_percent:.1f}%</b>',
            f'<ul>'
            f'<li>Solo en A: {stats["a"]}</li>'
            f'<li>Solo en B: {stats["b"]}</li>'
            f'<li>En ambos: {stats["both"]}</li>'
            f'<li>Sin coincidencia: {stats["none"]}</li>'
        ]
        if stats['skus_auto'] > 0:
            lines.append(f'<li>SKUs auto-asignados: {stats["skus_auto"]}</li>')
        lines.append('</ul>')

        if unmatched:
            lines.append(
                f'<b>⚠ {len(unmatched)} artículo(s) no encontrados en ningún catálogo '
                f'(requieren alta manual):</b><ul>'
            )
            lines.extend(f'<li>{item.lstrip("• ")}</li>' for item in unmatched)
            lines.append('</ul>')

        routing.message_post(
            body=''.join(lines),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

    def _build_result_html(self, routing, unmatched: list, stats: dict, threshold: float) -> str:
        warn_class = 'table-warning' if unmatched else ''
        assigned_a = len(routing.line_ids.filtered(
            lambda l: l.winner_partner_id == self.partner_a_id
        ))
        assigned_b = len(routing.line_ids.filtered(
            lambda l: l.winner_partner_id == self.partner_b_id
        ))
        total_amount = sum(routing.line_ids.mapped('detail_ids').mapped('subtotal'))

        html = f"""
        <div class="container-fluid">
            <div class="alert alert-success">
                <h4>Comparación de catálogos completada</h4>
                <p>Umbral aplicado: <strong>{self.threshold_percent:.1f}%</strong> —
                   se selecciona {self.partner_b_id.name} solo si su precio es
                   al menos {self.threshold_percent:.1f}%% más barato que {self.partner_a_id.name}.</p>
            </div>
            <table class="table table-sm table-bordered">
                <thead class="table-light">
                    <tr><th>Proveedor</th><th class="text-end">Artículos ganadores</th></tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>{self.partner_a_id.name}</strong> (preferido)</td>
                        <td class="text-end">{assigned_a}</td>
                    </tr>
                    <tr>
                        <td><strong>{self.partner_b_id.name}</strong> (alternativo)</td>
                        <td class="text-end">{assigned_b}</td>
                    </tr>
                    <tr class="{warn_class}">
                        <td>Sin coincidencia</td>
                        <td class="text-end">{stats['none']}</td>
                    </tr>
                </tbody>
                <tfoot class="table-light">
                    <tr>
                        <th>Total routing</th>
                        <th class="text-end">${total_amount:,.2f}</th>
                    </tr>
                </tfoot>
            </table>
        """
        if unmatched:
            html += f"""
            <div class="alert alert-warning">
                <strong>Artículos sin coincidencia ({len(unmatched)}) — requieren alta manual:</strong>
                <ul class="mb-0">
                    {''.join(f'<li>{item.lstrip("• ")}</li>' for item in unmatched)}
                </ul>
            </div>
            """
        html += '</div>'
        return html

    def action_back(self):
        self.write({'state': 'config'})
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
