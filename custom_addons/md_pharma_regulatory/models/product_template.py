from datetime import date

from markupsafe import Markup, escape

from odoo import api, fields, models

# Mismos umbrales que bi_pos_stock/static/src/app/utils/lot_expiry_utils.js
# (getExpiryColorClass / SHORT_EXPIRY_DAYS) — se replican server-side para
# que el Kanban de Inventario coincida exactamente con el criterio visual
# ya validado en la ProductCard del POS.
MD_LOT_EXPIRY_DANGER_DAYS = 30
MD_LOT_EXPIRY_WARNING_DAYS = 90
MD_SHORT_EXPIRY_DAYS = 180
MD_LOT_BREAKDOWN_LIMIT = 6

# Umbral de "stock bajo" para el badge semáforo de cantidad agregada
# (equivalente a pos.config.low_stock en la ProductCard del POS). Confirmado
# en vivo (2026-07-21) que las 12 configuraciones de POS en producción
# (todas las sucursales, incl. MDS MERIDA 1/2) tienen low_stock = 0.0, y la
# condición real en product_card.js es `threshold > 0 and qty <= threshold`
# — con threshold 0 el amarillo NUNCA se activa, solo verde/rojo. Se replica
# aquí el mismo valor y la misma condición para que el Kanban de Inventario
# sea un espejo exacto de lo que ve el cajero hoy, no un semáforo de 3
# estados que el POS real jamás muestra. Si algún día se sube low_stock > 0
# en alguna config de POS, actualizar este valor a mano (no hay lookup
# dinámico entre pos.config e Inventario — Inventario no está segmentado
# por sucursal).
MD_LOW_STOCK_THRESHOLD = 0


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    active_substance_ids = fields.Many2many(
        'md.active.substance', 'md_product_active_substance_rel',
        'product_tmpl_id', 'substance_id',
        string='Sustancia(s) Activa(s)',
    )
    l10n_mx_concentracion = fields.Char(string='Concentración')
    l10n_mx_forma_farmaceutica = fields.Char(string='Forma Farmacéutica')
    l10n_mx_registro_sanitario = fields.Char(string='Registro Sanitario (COFEPRIS)')
    l10n_mx_requiere_receta = fields.Boolean(string='Requiere Receta')
    l10n_mx_controlado = fields.Boolean(
        string='Controlado',
        help='Medicamento sujeto a control especial (grupos IV-VI, Ley General de Salud).',
    )
    l10n_mx_contenido_empaque = fields.Char(
        string='Contenido del Empaque',
        help='Cantidad/presentación por empaque extraída del nombre (ej. "C/100 ML", "C/30 CAPS").',
    )
    l10n_mx_dimensiones = fields.Char(
        string='Dimensiones',
        help='Medidas físicas del producto extraídas del nombre (ej. "18X15 CM").',
    )
    l10n_mx_tipo_envase = fields.Char(
        string='Tipo de Envase',
        help='Tipo de contenedor extraído del nombre (ej. "FRASCO", "ENVASE", "TUBO", "TARRO").',
    )
    l10n_mx_talla = fields.Char(
        string='Talla/Medida',
        help='Talla o medida abreviada extraída del nombre (ej. "CH", "MED", "GDE" -> "CHICO", "MEDIANO", "GRANDE").',
    )
    l10n_mx_tiene_iva = fields.Boolean(
        string='Tiene IVA', compute='_compute_l10n_mx_iva', store=True,
        help='Indica si el producto tiene un impuesto de venta del 16% (IVA) asociado.',
    )
    l10n_mx_iva_label = fields.Char(
        string='Etiqueta IVA', compute='_compute_l10n_mx_iva', store=True,
    )
    l10n_mx_price_con_iva = fields.Float(
        string='Precio con IVA', compute='_compute_l10n_mx_iva', store=True,
    )
    l10n_mx_nombre_homologado = fields.Char(
        string='Nombre Homologado (COFEPRIS)',
        help='Nombre propuesto: código de barras + nombre original + etiquetas regulatorias '
             '(sustancia, forma, concentración, contenido, envase, talla). No reemplaza a "name" '
             'hasta que se apruebe y se promueva explícitamente (evita romper documentos ya emitidos).',
    )
    l10n_mx_homologacion_state = fields.Selection([
        ('no_elegible', 'No elegible'),
        ('propuesto', 'Propuesto'),
        ('aprobado', 'Aprobado'),
        ('aplicado', 'Aplicado'),
    ], default='no_elegible', string='Estado de Homologación', required=True)
    l10n_mx_homologacion_fase = fields.Selection([
        ('fase_1_completo', 'Fase 1: datos completos'),
        ('fase_2_parcial', 'Fase 2: datos parciales'),
        ('fase_3_sin_datos', 'Fase 3: sin datos regulatorios'),
    ], string='Fase de Homologación')

    # ── Kanban de Inventario estilo POS: badge de existencia + lotes ────────
    # Replica el mismo lenguaje visual/umbrales de bi_pos_stock ProductCard
    # (ver models/bi_pos_lots.py::get_lots_expiry_summary/get_product_lots_detail)
    # pero a nivel product.template para el catálogo de Inventario, donde no
    # existe el concepto de "lote seleccionado en el carrito" del POS — en su
    # lugar se muestra el desglose completo de lotes a la mano (FEFO).
    md_has_short_expiry = fields.Boolean(
        string='Próx. Vencer',
        compute='_compute_md_lot_expiry_info',
        help='Al menos un lote a la mano vence en %s días o menos.' % MD_SHORT_EXPIRY_DAYS,
    )
    md_nearest_expiry_color = fields.Char(compute='_compute_md_lot_expiry_info')
    md_lot_breakdown_html = fields.Html(
        string='Lotes a la Mano',
        compute='_compute_md_lot_expiry_info',
        sanitize=False,
    )
    md_onhand_badge_color = fields.Char(
        string='Color badge A la mano',
        compute='_compute_md_onhand_badge_color',
    )

    @api.depends('qty_available')
    def _compute_md_onhand_badge_color(self):
        for product in self:
            qty = product.qty_available
            threshold = MD_LOW_STOCK_THRESHOLD
            # Misma condición que stockColorClass en product_card.js
            # (`threshold > 0 and qty <= threshold`), no solo el mismo valor.
            if qty <= 0:
                product.md_onhand_badge_color = 'danger'
            elif threshold > 0 and qty <= threshold:
                product.md_onhand_badge_color = 'warning'
            else:
                product.md_onhand_badge_color = 'success'

    def _md_onhand_lot_locations(self):
        """Mismo criterio que stock.lot._get_qty_a_la_mano_locations
        (md_lots_management): ubicaciones internas de las compañías activas."""
        return self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', 'in', list(self.env.companies.ids) + [False]),
        ])

    @staticmethod
    def _md_days_left(date_str):
        if not date_str:
            return None
        return (fields.Date.from_string(date_str) - date.today()).days

    @classmethod
    def _md_expiry_color(cls, date_str):
        days = cls._md_days_left(date_str)
        if days is None:
            return 'secondary'
        if days <= MD_LOT_EXPIRY_DANGER_DAYS:
            return 'danger'
        if days <= MD_LOT_EXPIRY_WARNING_DAYS:
            return 'warning'
        return 'success'

    @classmethod
    def _md_is_short_expiry(cls, date_str):
        days = cls._md_days_left(date_str)
        return days is not None and days <= MD_SHORT_EXPIRY_DAYS

    @staticmethod
    def _md_format_qty(qty):
        return str(int(qty)) if float(qty).is_integer() else '%.2f' % qty

    def _md_render_lot_breakdown(self, lots):
        chips = []
        for lot in lots[:MD_LOT_BREAKDOWN_LIMIT]:
            color = self._md_expiry_color(lot['expiration_date'])
            date_label = lot['expiration_date'] or '—'
            qty_label = self._md_format_qty(lot['qty'])
            chips.append(Markup(
                '<span class="badge bg-%s md-lot-chip">'
                '<i class="fa fa-calendar me-1"></i>%s'
                '<span class="mx-1">&middot;</span>'
                '<i class="fa fa-cubes me-1"></i>%s'
                '</span>'
            ) % (color, escape(date_label), escape(qty_label)))
        remaining = len(lots) - MD_LOT_BREAKDOWN_LIMIT
        if remaining > 0:
            chips.append(Markup('<span class="badge bg-secondary md-lot-chip">+%d</span>') % remaining)
        return Markup('<div class="d-flex flex-wrap gap-1">%s</div>') % Markup('').join(chips)

    def _md_lot_breakdown_data(self):
        """FEFO-sorted lot list para self (un solo producto): [{lot_id,
        lot_name, expiration_date, qty}, ...]. Extraído de
        _compute_md_lot_expiry_info para reutilizarse también en
        get_md_lot_detail() (RPC del popup FEFO del Kanban de Inventario,
        equivalente a pos.session.get_product_lots_detail del POS)."""
        self.ensure_one()
        if self.tracking not in ('lot', 'serial') or not self.product_variant_ids:
            return []

        has_expiry = 'expiration_date' in self.env['stock.lot']._fields
        location_ids = self._md_onhand_lot_locations().ids

        quants = self.env['stock.quant'].sudo().search_read(
            domain=[
                ('product_id', 'in', self.product_variant_ids.ids),
                ('location_id', 'in', location_ids),
                ('lot_id', '!=', False),
                ('quantity', '>', 0),
            ],
            fields=['lot_id', 'quantity'],
        )
        if not quants:
            return []

        qty_by_lot = {}
        for quant in quants:
            lot_id = quant['lot_id'][0]
            qty_by_lot[lot_id] = qty_by_lot.get(lot_id, 0.0) + quant['quantity']

        expiry_by_lot = {}
        if has_expiry:
            lots_data = self.env['stock.lot'].sudo().search_read(
                domain=[('id', 'in', list(qty_by_lot.keys()))],
                fields=['id', 'name', 'expiration_date'],
            )
            for lot_data in lots_data:
                exp = lot_data.get('expiration_date')
                expiry_by_lot[lot_data['id']] = {
                    'name': lot_data['name'],
                    'expiration_date': exp.strftime('%Y-%m-%d') if exp else None,
                }

        lots = []
        for lot_id, qty in qty_by_lot.items():
            info = expiry_by_lot.get(lot_id, {'name': str(lot_id), 'expiration_date': None})
            lots.append({
                'lot_id': lot_id,
                'lot_name': info['name'],
                'expiration_date': info['expiration_date'],
                'qty': qty,
            })
        lots.sort(key=lambda l: (l['expiration_date'] is None, l['expiration_date'] or ''))
        return lots

    @api.depends_context('company')
    def _compute_md_lot_expiry_info(self):
        for template in self:
            template.md_has_short_expiry = False
            template.md_nearest_expiry_color = 'secondary'
            template.md_lot_breakdown_html = ''

            lots = template._md_lot_breakdown_data()
            if not lots:
                continue

            nearest = lots[0]
            template.md_nearest_expiry_color = self._md_expiry_color(nearest['expiration_date'])
            template.md_has_short_expiry = self._md_is_short_expiry(nearest['expiration_date'])
            template.md_lot_breakdown_html = self._md_render_lot_breakdown(lots)

    def get_md_lot_detail(self):
        """RPC del boton dedicado "detalle de lotes FEFO" en el Kanban de
        Inventario (kanban_lot_detail_popup.js) — equivalente a
        pos.session.get_product_lots_detail() del POS, pero sin acotar a
        una sola sucursal/sesión (Inventario agrega existencias de todas
        las compañías activas, ver _md_onhand_lot_locations). Devuelve la
        lista COMPLETA (sin el límite de MD_LOT_BREAKDOWN_LIMIT chips que sí
        aplica al resumen inline de la card, _md_render_lot_breakdown)."""
        self.ensure_one()
        return self._md_lot_breakdown_data()

    @api.depends('list_price', 'taxes_id', 'taxes_id.amount')
    def _compute_l10n_mx_iva(self):
        for product in self:
            iva = product.taxes_id.filtered(lambda t: t.amount == 16.0)[:1]
            if iva:
                product.l10n_mx_tiene_iva = True
                product.l10n_mx_iva_label = 'IVA %s%%' % int(iva.amount)
                product.l10n_mx_price_con_iva = product.list_price * (1 + iva.amount / 100.0)
            else:
                product.l10n_mx_tiene_iva = False
                product.l10n_mx_iva_label = False
                product.l10n_mx_price_con_iva = product.list_price

    def action_open_cofepris_detail(self):
        """Abre el detalle regulatorio COFEPRIS en un modal de solo lectura.

        Equivalente en Inventario al boton (i) de la ProductCard del POS
        (bi_pos_stock LotDetailPopup, rama "Detalle regulatorio"), pero
        reutilizando los campos ya existentes en la pestaña "Regulacion
        COFEPRIS" del formulario de producto (views/product_template_views.xml)
        en vez de un popup OWL nuevo -- mismo patron nativo de Odoo backend
        (act_window con target=new) usado en otros botones de este proyecto.
        """
        self.ensure_one()
        view_id = self.env.ref('md_pharma_regulatory.view_product_template_cofepris_detail_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detalle Regulatorio COFEPRIS',
            'res_model': 'product.template',
            'res_id': self.id,
            'views': [[view_id, 'form']],
            'target': 'new',
        }
