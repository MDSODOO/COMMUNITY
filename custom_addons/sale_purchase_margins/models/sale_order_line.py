# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero

from .margin_tools import get_standard_cost_for_line, normalize_margin_key

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    qfm_margin_pct = fields.Float(
        string='Margen Venta (%)',
        compute='_compute_qfm_sale_margin',
        inverse='_inverse_qfm_margin_pct',
        store=False,
        readonly=False,
        digits=(16, 2),
        help=(
            'Margen comercial sobre precio de venta neto: '
            '(precio_neto - costo_estandar) / precio_neto * 100. '
            'Si el precio de venta neto es 0, el porcentaje se muestra como 0% '
            'aunque exista costo (ratio matematicamente indefinido). '
            'Editable: al cambiarlo se recalcula price_unit conservando el descuento.'
        ),
    )

    qfm_margin_abs = fields.Float(
        string='Margen Venta (Importe)',
        compute='_compute_qfm_sale_margin',
        store=False,
        readonly=True,
        digits=(16, 2),
        help=(
            'Importe de margen de venta: (precio_neto - costo_estandar) * cantidad. '
            'Puede resultar negativo si el precio de venta esta debajo del costo.'
        ),
    )

    @api.depends(
        'price_unit',
        'discount',
        'product_id',
        'product_id.standard_price',
        'product_uom_id',
        'product_uom_qty',
        'order_id.currency_id',
        'order_id.company_id',
        'order_id.date_order',
    )
    def _compute_qfm_sale_margin(self):
        for line in self:
            line.qfm_margin_pct = 0.0
            line.qfm_margin_abs = 0.0
            try:
                costo_unitario = get_standard_cost_for_line(line, 'product_uom_id')
                descuento = min(max(line.discount or 0.0, 0.0), 100.0)
                precio_venta = (line.price_unit or 0.0) * (1.0 - descuento / 100.0)
                cantidad = line.product_uom_qty or 0.0

                if precio_venta > 0:
                    line.qfm_margin_pct = (precio_venta - costo_unitario) / precio_venta * 100.0
                line.qfm_margin_abs = (precio_venta - costo_unitario) * cantidad
            except (UserError, ValidationError):
                raise
            except Exception:
                _logger.exception(
                    'QFM margins: no se pudo calcular margen de venta para linea %s',
                    line.id or 'new',
                )

    @api.model
    def _qfm_relation_display_name(self, record):
        if not record:
            return ''
        for field_name in ('x_name', 'name', 'x_studio_name'):
            if field_name in record._fields and record[field_name]:
                return record[field_name]
        return record.display_name or ''

    @api.model
    @tools.ormcache()
    def _qfm_product_line_field_name(self):
        field_candidates = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'product.template'),
            ('relation', '=', 'x_line'),
            ('ttype', 'in', ('many2one', 'many2many')),
        ])
        if not field_candidates:
            return False

        def _score(field):
            name = (field.name or '').lower()
            label = (field.field_description or '').lower()
            text = f'{name} {label}'
            return (
                0 if 'line' in text or 'línea' in text or 'linea' in text else 1,
                0 if 'studio' not in name else 1,
                field.id,
            )

        return field_candidates.sorted(_score)[:1].name

    def _qfm_get_product_line_names(self):
        self.ensure_one()
        if not self.product_id:
            return []

        product_tmpl = self.product_id.product_tmpl_id.sudo()
        line_field_name = self._qfm_product_line_field_name()
        if not line_field_name or line_field_name not in product_tmpl._fields:
            return []

        line_records = product_tmpl[line_field_name].sudo()
        if not line_records:
            return []

        names = []
        for line in line_records:
            line_name = (self._qfm_relation_display_name(line) or '').strip()
            if line_name:
                names.append(line_name)
        return sorted(set(names))

    def _qfm_get_configured_margin_from_line(self):
        self.ensure_one()
        line_names = self._qfm_get_product_line_names()
        if not line_names:
            return False

        rules_model = self.env['qfm.sale.margin.line.rule']
        company = self.order_id.company_id or self.env.company
        line_keys = [normalize_margin_key(name) for name in line_names]
        line_keys = [key for key in line_keys if key]
        if not line_keys:
            return False

        rules = rules_model.search([
            ('active', '=', True),
            ('line_key', 'in', line_keys),
            ('company_id', 'in', [company.id, False]),
        ])
        if not rules:
            return False

        # Índice en memoria con prioridad: regla específica de compañía.
        rules_by_key = {}
        for rule in rules:
            key = rule.line_key
            current = rules_by_key.get(key)
            if not current:
                rules_by_key[key] = rule
                continue
            if not current.company_id and rule.company_id:
                rules_by_key[key] = rule

        for line_key in line_keys:
            rule = rules_by_key.get(line_key)
            if rule:
                return rule.margin_pct
        return False

    @api.onchange('product_id')
    def _onchange_qfm_set_margin_from_product_line(self):
        if not self.product_id:
            return
        margin_pct = self._qfm_get_configured_margin_from_line()
        if margin_pct is False:
            return

        self.qfm_margin_pct = margin_pct
        try:
            self._qfm_apply_target_margin_to_price_unit()
        except ValidationError as err:
            return {
                'warning': {
                    'title': _('No se pudo aplicar margen por linea'),
                    'message': str(err),
                }
            }

    def _qfm_apply_target_margin_to_price_unit(self):
        for line in self:
            if not line.product_id:
                continue

            margen_objetivo = line.qfm_margin_pct or 0.0
            if margen_objetivo < 0.0:
                raise ValidationError(_('El margen objetivo no puede ser negativo.'))
            if margen_objetivo >= 100.0:
                raise ValidationError(_('El margen objetivo debe ser menor a 100%.'))

            descuento = min(max(line.discount or 0.0, 0.0), 100.0)
            factor_descuento = 1.0 - descuento / 100.0
            if factor_descuento <= 0.0:
                raise ValidationError(
                    _('Con un descuento del 100% no se puede calcular el precio unitario.')
                )

            try:
                costo_unitario = get_standard_cost_for_line(line, 'product_uom_id')
            except (UserError, ValidationError):
                raise
            except Exception:
                _logger.exception(
                    'QFM margins: no se pudo calcular precio desde margen para linea %s',
                    line.id or 'new',
                )
                continue

            if costo_unitario <= 0.0:
                raise ValidationError(_(
                    'El producto %s no tiene costo estándar definido. '
                    'Configura el costo antes de aplicar un margen objetivo.'
                ) % line.product_id.display_name)

            precio_venta_neto = costo_unitario / (1.0 - margen_objetivo / 100.0)
            precio_unitario_nuevo = precio_venta_neto / factor_descuento

            currency = line.order_id.currency_id or line.env.company.currency_id
            if currency:
                precio_unitario_nuevo = currency.round(precio_unitario_nuevo)

            if float_is_zero(
                (line.price_unit or 0.0) - precio_unitario_nuevo,
                precision_digits=6,
            ):
                continue

            line.price_unit = precio_unitario_nuevo

    def _inverse_qfm_margin_pct(self):
        if self.env.context.get('_qfm_applying_margin'):
            return
        self.with_context(_qfm_applying_margin=True)._qfm_apply_target_margin_to_price_unit()

    @api.onchange('qfm_margin_pct')
    def _onchange_qfm_margin_pct_set_price_unit(self):
        try:
            self._qfm_apply_target_margin_to_price_unit()
        except ValidationError as err:
            return {
                'warning': {
                    'title': _('Margen objetivo invalido'),
                    'message': str(err),
                }
            }

    @api.onchange('product_id', 'price_unit', 'product_uom_id', 'product_uom_qty', 'discount')
    def _onchange_qfm_margin_warning(self):
        if self.product_id and self.price_unit:
            try:
                costo = get_standard_cost_for_line(self, 'product_uom_id')
                descuento = min(max(self.discount or 0.0, 0.0), 100.0)
                precio_venta = (self.price_unit or 0.0) * (1.0 - descuento / 100.0)
            except (UserError, ValidationError):
                raise
            except Exception:
                _logger.exception(
                    'QFM margins: no se pudo evaluar alerta de venta para linea %s',
                    self.id or 'new',
                )
                return
            if precio_venta < costo:
                return {
                    'warning': {
                        'title': 'Margen Negativo Detectado',
                        'message': (
                            f'El precio de venta (${precio_venta:.2f}) es MENOR '
                            f'al costo estándar (${costo:.2f}).\n\n'
                            f'Esto generará un margen NEGATIVO.'
                        ),
                    }
                }
