from odoo import models, fields
from odoo.exceptions import UserError

from .price_notification import _get_product_line_field_name


class PriceNotificationReportWizard(models.TransientModel):
    _name = 'purchase.price.notification.report.wizard'
    _description = 'Asistente: Reporte de Cambios de Precio'

    # "Línea" (fabricante/laboratorio, p. ej. ACCORD/JALOMA) se modela con
    # md.product.line (módulo md_product_lines, 97% de productos poblados).
    # Una migración previa usó product.category aquí por error conceptual
    # (confundió "Línea" con la taxonomía interna genérica de Odoo, que en
    # este proyecto solo tiene 6 registros y está reservada para otro fin
    # -- ver docs/plans/X_LINE_DEPENDENCY_MIGRATION_OPTIONS.md).
    line_ids = fields.Many2many(
        'md.product.line',
        string='Línea de Producto',
    )
    company_ids = fields.Many2many(
        'res.company',
        string='Sucursales',
        default=lambda self: self.env['res.company'].sudo().search([]),
    )
    state = fields.Selection([
        ('all', 'Todas'),
        ('unread', 'Sin leer'),
        ('read', 'Leídas'),
        ('applied', 'Aplicadas'),
    ], string='Estado', default='all')

    def _build_domain(self):
        domain = [('company_id', 'in',
                   self.company_ids.ids or self.env['res.company'].sudo().search([]).ids)]
        if self.state != 'all':
            domain.append(('state', '=', self.state))
        # Filtro por Línea de producto (md.product.line): detecta el campo
        # dinámico en product.template vía metadata real (ir.model.fields).
        if self.line_ids:
            line_field = _get_product_line_field_name(self.env)
            if line_field:
                matching = self.env['product.template'].search([
                    (line_field, 'in', self.line_ids.ids)
                ])
                if matching:
                    domain.append(('product_tmpl_id', 'in', matching.ids))
        return domain

    def action_print_report(self):
        self.ensure_one()
        docs = self.env['purchase.price.notification'].search(self._build_domain())
        if not docs:
            raise UserError("No hay notificaciones que coincidan con los filtros seleccionados.")
        return self.env.ref(
            'purchase_invoice_parser.action_purchase_price_change_report'
        ).report_action(docs.ids)

    def action_export_excel(self):
        self.ensure_one()
        docs = self.env['purchase.price.notification'].search(self._build_domain())
        if not docs:
            raise UserError("No hay notificaciones que coincidan con los filtros seleccionados.")
        co_ids = self.company_ids.ids or None
        return docs.action_export_price_change_excel(company_ids=co_ids)
