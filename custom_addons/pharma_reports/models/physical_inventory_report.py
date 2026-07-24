# -*- coding: utf-8 -*-
import base64
import datetime
import io

from odoo import api, fields, models
from odoo.exceptions import UserError


class ReportPhysicalInventoryDocument(models.AbstractModel):
    _name = 'report.pharma_reports.report_physical_inventory_document'
    _description = 'Reporte PDF de Inventario Físico'

    _DEFAULT_ADJUSTMENT_REASON = 'Ajuste por conteo físico'
    _REASON_FIELD_CANDIDATES = (
        'inventory_reason_id',
        'inventory_reason',
        'adjustment_reason_id',
        'adjustment_reason',
        'reason_id',
        'reason',
        'x_studio_motivo',
        'x_motivo',
        'x_studio_reason',
        'x_reason',
    )

    def _get_product_line_field_name(self):
        """Return the field name linking product.template to md.product.line
        (módulo md_product_lines -- reemplaza al x_line de Studio, que quedó
        con 0% de productos poblados; product_line_id tiene 97% de cobertura
        real, ver docs/plans/X_LINE_DEPENDENCY_MIGRATION_OPTIONS.md)."""
        if 'md.product.line' not in self.env.registry.models:
            return False

        fields = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'product.template'),
            ('relation', '=', 'md.product.line'),
            ('ttype', 'in', ('many2one', 'many2many')),
        ])
        if not fields:
            return False

        def score(field):
            name = (field.name or '').lower()
            label = (field.field_description or '').lower()
            text = f'{name} {label}'
            return (
                0 if 'line' in text or 'linea' in text or 'línea' in text else 1,
                0 if 'studio' not in name else 1,
                field.id,
            )

        return fields.sorted(score)[:1].name

    def _get_product_line_name(self, product, field_name):
        if not field_name:
            return '—'

        template = product.product_tmpl_id
        if not template or field_name not in template._fields:
            return '—'

        value = template[field_name]
        if not value:
            return '—'

        return ', '.join(value.mapped('display_name')) if hasattr(value, 'mapped') else str(value)

    def _get_adjustment_reason_field_names(self):
        dynamic_names = []
        reason_fields = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'stock.quant'),
            ('ttype', 'in', ('char', 'text', 'selection', 'many2one', 'many2many')),
        ])
        tokens = ('motivo', 'reason', 'razon', 'razón', 'causa', 'justific')
        for field in reason_fields:
            text = f'{field.name or ""} {field.field_description or ""}'.lower()
            if any(token in text for token in tokens):
                dynamic_names.append(field.name)

        return list(dict.fromkeys(self._REASON_FIELD_CANDIDATES + tuple(dynamic_names)))

    def _stringify_adjustment_reason(self, value):
        if not value or value is True:
            return ''
        if hasattr(value, 'mapped'):
            return ', '.join(value.mapped('display_name'))
        return str(value).strip()

    def _get_adjustment_reason(self, docs, data=None):
        data = data or {}
        explicit_reason = data.get('adjustment_reason') or data.get('reason') or data.get('motivo')
        if explicit_reason:
            return explicit_reason

        reasons = []
        reason_field_names = self._get_adjustment_reason_field_names()
        for quant in docs:
            for field_name in reason_field_names:
                if field_name not in quant._fields:
                    continue
                reason = self._stringify_adjustment_reason(quant[field_name])
                if reason:
                    reasons.append(reason)
                    break

        unique_reasons = list(dict.fromkeys(reasons))
        return ', '.join(unique_reasons) if unique_reasons else self._DEFAULT_ADJUSTMENT_REASON

    def _format_qty(self, value):
        return f'{abs(value):.2f}'

    def _format_money(self, value):
        return f'$ {abs(value):.2f}'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['stock.quant'].browse(docids)
        company = docs[0].company_id.sudo() if docs else self.env.company
        line_field = self._get_product_line_field_name()

        line_names = {}
        product_names = {}
        unit_costs = {}
        on_hand_values = {}
        counted_values = {}

        counted_quants = docs.filtered(lambda q: q.inventory_quantity_set)
        location_summaries = {}

        total_on_hand_value = 0.0
        total_counted_value = 0.0
        counted_on_hand_qty = 0.0
        counted_qty = 0.0
        counted_on_hand_value = 0.0

        for quant in docs:
            product = quant.product_id
            product_company = product.with_company(company).sudo() if company else product.sudo()
            unit_cost = product_company.standard_price or 0.0
            on_hand_value = (quant.quantity or 0.0) * unit_cost
            counted_value = (quant.inventory_quantity or 0.0) * unit_cost if quant.inventory_quantity_set else 0.0
            location_id = quant.location_id.id

            line_names[quant.id] = self._get_product_line_name(product, line_field)
            product_names[quant.id] = product.with_context(display_default_code=False).display_name or product.name or ''
            unit_costs[quant.id] = unit_cost
            on_hand_values[quant.id] = on_hand_value
            counted_values[quant.id] = counted_value

            total_on_hand_value += on_hand_value
            if quant.inventory_quantity_set:
                total_counted_value += counted_value
                counted_on_hand_qty += quant.quantity or 0.0
                counted_qty += quant.inventory_quantity or 0.0
                counted_on_hand_value += on_hand_value

            summary = location_summaries.setdefault(location_id, {
                'on_hand_value': 0.0,
                'counted_value': 0.0,
                'counted_on_hand_value': 0.0,
            })
            summary['on_hand_value'] += on_hand_value
            if quant.inventory_quantity_set:
                summary['counted_value'] += counted_value
                summary['counted_on_hand_value'] += on_hand_value

        variation_qty = counted_qty - counted_on_hand_qty
        variation_value = total_counted_value - counted_on_hand_value

        summary = {
            'total_on_hand_value': total_on_hand_value,
            'total_counted_value': total_counted_value,
            'counted_on_hand_qty': counted_on_hand_qty,
            'counted_qty': counted_qty,
            'variation_qty': variation_qty,
            'variation_value': variation_value,
            'variation_qty_fmt': self._format_qty(variation_qty),
            'variation_value_fmt': self._format_money(variation_value),
        }

        return {
            'doc_ids': docids,
            'doc_model': 'stock.quant',
            'docs': docs,
            'company': company,
            'datetime': datetime,
            'user': self.env.user,
            'adjustment_reason': self._get_adjustment_reason(docs, data=data),
            'line_names': line_names,
            'product_names': product_names,
            'unit_costs': unit_costs,
            'on_hand_values': on_hand_values,
            'counted_values': counted_values,
            'location_summaries': location_summaries,
            'summary': summary,
        }


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def action_export_physical_inventory_excel(self):
        docs = self.exists()
        if not docs:
            raise UserError('Selecciona al menos una línea de inventario físico para exportar.')

        try:
            import xlsxwriter
        except ImportError as exc:
            raise UserError('xlsxwriter no disponible en el servidor.') from exc

        report_model = self.env['report.pharma_reports.report_physical_inventory_document']
        report_values = report_model._get_report_values(docs.ids)
        docs = report_values['docs']
        company = report_values.get('company') or self.env.company
        locations = docs.mapped('location_id')
        user_ids = docs.mapped('user_id').filtered(lambda user: user.id)
        solicita = ', '.join(user_ids.mapped('name')[:2]) if user_ids else '—'
        location_label = ', '.join(locations.mapped('display_name')[:2]) if locations else '—'
        if len(locations) > 2:
            location_label = f'{location_label} +{len(locations) - 2}'

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Inventario Fisico')

        brand = '#234759'
        teal = '#4DB39C'
        lime = '#8DC63F'
        cream = '#F3F3F3'
        border = '#D3D3D3'
        ink = '#1A2332'
        ink_2 = '#374151'
        row_neg = '#FFF5F5'
        row_pos = '#F0FFF4'
        row_ok = '#F7FBFF'

        title_fmt = workbook.add_format({
            'bold': True,
            'font_size': 15,
            'font_color': brand,
            'align': 'left',
            'valign': 'vcenter',
            'bottom': 2,
            'bottom_color': brand,
        })
        meta_label_fmt = workbook.add_format({
            'bold': True,
            'font_size': 8,
            'font_color': '#6B7280',
            'bg_color': cream,
            'border': 1,
            'border_color': border,
            'valign': 'vcenter',
        })
        meta_value_fmt = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font_color': ink,
            'bg_color': cream,
            'border': 1,
            'border_color': border,
            'valign': 'vcenter',
            'text_wrap': True,
        })
        header_fmt = workbook.add_format({
            'bold': True,
            'font_size': 8,
            'font_color': '#FFFFFF',
            'bg_color': teal,
            'border': 1,
            'border_color': '#FFFFFF',
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        location_fmt = workbook.add_format({
            'bold': True,
            'font_size': 9,
            'font_color': '#FFFFFF',
            'bg_color': brand,
            'border': 1,
            'border_color': brand,
            'valign': 'vcenter',
        })
        total_label_fmt = workbook.add_format({
            'bold': True,
            'font_size': 9,
            'font_color': '#FFFFFF',
            'bg_color': brand,
            'border': 1,
            'border_color': brand,
            'valign': 'vcenter',
        })
        total_num_fmt = workbook.add_format({
            'bold': True,
            'font_size': 9,
            'font_color': '#FFFFFF',
            'bg_color': brand,
            'border': 1,
            'border_color': brand,
            'num_format': '#,##0.00',
            'align': 'right',
        })
        total_money_fmt = workbook.add_format({
            'bold': True,
            'font_size': 9,
            'font_color': '#FFFFFF',
            'bg_color': brand,
            'border': 1,
            'border_color': brand,
            'num_format': '$ #,##0.00',
            'align': 'right',
        })

        def body_formats(fill_color=None):
            base = {
                'font_size': 8,
                'font_color': ink_2,
                'border': 1,
                'border_color': border,
                'valign': 'top',
            }
            if fill_color:
                base['bg_color'] = fill_color
            left = workbook.add_format({**base, 'text_wrap': True})
            mono = workbook.add_format({**base, 'font_name': 'Courier New', 'text_wrap': True})
            num = workbook.add_format({**base, 'num_format': '#,##0.00', 'align': 'right'})
            money = workbook.add_format({**base, 'num_format': '$ #,##0.00', 'align': 'right'})
            return left, mono, num, money

        cell_default, mono_default, num_default, money_default = body_formats()
        cell_neg, mono_neg, num_neg, money_neg = body_formats(row_neg)
        cell_pos, mono_pos, num_pos, money_pos = body_formats(row_pos)
        cell_ok, mono_ok, num_ok, money_ok = body_formats(row_ok)
        diff_neg_fmt = workbook.add_format({
            'bold': True,
            'font_size': 8,
            'font_color': '#DC2626',
            'bg_color': row_neg,
            'border': 1,
            'border_color': border,
            'num_format': '#,##0.00',
            'align': 'right',
        })
        diff_pos_fmt = workbook.add_format({
            'bold': True,
            'font_size': 8,
            'font_color': '#16A34A',
            'bg_color': row_pos,
            'border': 1,
            'border_color': border,
            'num_format': '#,##0.00',
            'align': 'right',
        })
        diff_zero_fmt = workbook.add_format({
            'font_size': 8,
            'font_color': '#6B7280',
            'bg_color': row_ok,
            'border': 1,
            'border_color': border,
            'num_format': '#,##0.00',
            'align': 'right',
        })

        columns = [
            ('Línea', 13),
            ('Código', 16),
            ('Producto', 34),
            ('Lote', 14),
            ('Caducidad', 12),
            ('A la mano', 10),
            ('Contada', 10),
            ('Δ', 10),
            ('Costo Unit.', 12),
            ('Costo A la mano', 14),
            ('Costo contado', 14),
        ]
        for col, (_label, width) in enumerate(columns):
            sheet.set_column(col, col, width)

        sheet.merge_range(0, 0, 0, 10, 'Ajuste de Inventario', title_fmt)
        sheet.set_row(0, 26)
        sheet.set_row(2, 18)
        sheet.set_row(3, 34)

        today = fields.Date.context_today(self)
        date_label = today.strftime('%d/%m/%Y')
        meta_blocks = [
            (0, 1, 'Empresa', company.name or '—'),
            (2, 3, 'Sucursal', location_label),
            (4, 5, 'Solicita', solicita),
            (6, 7, 'Realiza', self.env.user.name or '—'),
            (8, 8, 'Fecha del ajuste', date_label),
            (9, 10, 'Motivo', report_values.get('adjustment_reason') or '—'),
        ]
        for start_col, end_col, label, value in meta_blocks:
            if start_col == end_col:
                sheet.write(2, start_col, label.upper(), meta_label_fmt)
                sheet.write(3, start_col, value, meta_value_fmt)
            else:
                sheet.merge_range(2, start_col, 2, end_col, label.upper(), meta_label_fmt)
                sheet.merge_range(3, start_col, 3, end_col, value, meta_value_fmt)

        header_row = 5
        for col, (label, _width) in enumerate(columns):
            sheet.write(header_row, col, label, header_fmt)
        sheet.freeze_panes(header_row + 1, 0)
        sheet.autofilter(header_row, 0, header_row, len(columns) - 1)

        row = header_row + 1
        line_names = report_values['line_names']
        product_names = report_values['product_names']
        unit_costs = report_values['unit_costs']
        on_hand_values = report_values['on_hand_values']
        counted_values = report_values['counted_values']

        for location in locations:
            sheet.merge_range(row, 0, row, 10, location.display_name, location_fmt)
            row += 1

            loc_quants = docs.filtered(lambda quant: quant.location_id.id == location.id)
            for quant in loc_quants:
                if quant.inventory_quantity_set and quant.inventory_diff_quantity < 0:
                    cell_fmt, mono_fmt, num_fmt, money_fmt = cell_neg, mono_neg, num_neg, money_neg
                    diff_fmt = diff_neg_fmt
                elif quant.inventory_quantity_set and quant.inventory_diff_quantity > 0:
                    cell_fmt, mono_fmt, num_fmt, money_fmt = cell_pos, mono_pos, num_pos, money_pos
                    diff_fmt = diff_pos_fmt
                elif quant.inventory_quantity_set:
                    cell_fmt, mono_fmt, num_fmt, money_fmt = cell_ok, mono_ok, num_ok, money_ok
                    diff_fmt = diff_zero_fmt
                else:
                    cell_fmt, mono_fmt, num_fmt, money_fmt = (
                        cell_default, mono_default, num_default, money_default
                    )
                    diff_fmt = num_fmt

                product = quant.product_id
                expiration = (
                    quant.expiration_date.strftime('%d/%m/%Y')
                    if quant.expiration_date
                    else ''
                )
                sheet.write(row, 0, line_names.get(quant.id, '—'), cell_fmt)
                sheet.write(row, 1, product.barcode or product.default_code or '', mono_fmt)
                sheet.write(row, 2, product_names.get(quant.id, product.name or ''), cell_fmt)
                sheet.write(row, 3, quant.lot_id.name or '', mono_fmt)
                sheet.write(row, 4, expiration, mono_fmt)
                sheet.write_number(row, 5, quant.quantity or 0.0, num_fmt)
                if quant.inventory_quantity_set:
                    sheet.write_number(row, 6, quant.inventory_quantity or 0.0, num_fmt)
                    sheet.write_number(row, 7, quant.inventory_diff_quantity or 0.0, diff_fmt)
                    sheet.write_number(row, 10, counted_values.get(quant.id, 0.0), money_fmt)
                else:
                    sheet.write(row, 6, '—', cell_fmt)
                    sheet.write(row, 7, '—', cell_fmt)
                    sheet.write(row, 10, '—', cell_fmt)
                sheet.write_number(row, 8, unit_costs.get(quant.id, 0.0), money_fmt)
                sheet.write_number(row, 9, on_hand_values.get(quant.id, 0.0), money_fmt)
                row += 1

        all_counted = docs.filtered(lambda quant: quant.inventory_quantity_set)
        summary = report_values['summary']
        sheet.merge_range(row, 0, row, 4, 'TOTAL GENERAL', total_label_fmt)
        sheet.write_number(row, 5, sum(docs.mapped('quantity')), total_num_fmt)
        if all_counted:
            sheet.write_number(row, 6, sum(all_counted.mapped('inventory_quantity')), total_num_fmt)
            total_diff_quantity = sum(all_counted.mapped('inventory_diff_quantity'))
            sheet.write_number(row, 7, total_diff_quantity, total_num_fmt)
            sheet.write_number(row, 10, summary.get('total_counted_value', 0.0), total_money_fmt)
        else:
            sheet.write(row, 6, '—', total_label_fmt)
            sheet.write(row, 7, '—', total_label_fmt)
            sheet.write(row, 10, '—', total_label_fmt)
        sheet.write(row, 8, '', total_label_fmt)
        sheet.write_number(row, 9, summary.get('total_on_hand_value', 0.0), total_money_fmt)

        workbook.close()
        output.seek(0)

        filename = f'inventario_fisico_{today.strftime("%Y%m%d")}.xlsx'
        attachment = self.env['ir.attachment'].sudo().create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()).decode('ascii'),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'stock.quant',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
