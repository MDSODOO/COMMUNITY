# -*- coding: utf-8 -*-
"""
Wizard para crear solicitudes de descarga masiva de forma rápida.
Permite seleccionar rangos predefinidos (mes anterior, trimestre, etc.)
"""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class SatDownloadWizard(models.TransientModel):
    _name = 'sat.download.wizard'
    _description = 'Asistente de Descarga Masiva SAT'

    company_id = fields.Many2one(
        'res.company',
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    date_range = fields.Selection(
        selection=[
            ('custom', 'Personalizado'),
            ('current_month', 'Mes Actual'),
            ('last_month', 'Mes Anterior'),
            ('last_quarter', 'Trimestre Anterior'),
            ('last_year', 'Año Anterior'),
        ],
        string="Rango de Fechas",
        default='last_month',
    )
    date_from = fields.Date(
        string="Fecha Inicio",
    )
    date_to = fields.Date(
        string="Fecha Fin",
    )
    download_type = fields.Selection(
        selection=[
            ('received', 'Recibidos'),
            ('issued', 'Emitidos'),
        ],
        string="Tipo",
        required=True,
        default='received',
    )
    request_type = fields.Selection(
        selection=[
            ('CFDI', 'CFDI (XML completo)'),
            ('Metadata', 'Metadata'),
        ],
        string="Tipo de Solicitud",
        default='CFDI',
        required=True,
    )
    voucher_type = fields.Selection(
        selection=[
            ('', 'Todos'),
            ('I', 'Ingreso'),
            ('E', 'Egreso'),
            ('T', 'Traslado'),
            ('N', 'Nómina'),
            ('P', 'Pago'),
        ],
        string="Tipo de Comprobante",
        default='',
    )
    fiel_valid = fields.Boolean(
        related='company_id.l10n_mx_sat_fiel_valid',
        string="FIEL Válida",
    )

    @api.onchange('date_range')
    def _onchange_date_range(self):
        today = date.today()
        if self.date_range == 'current_month':
            self.date_from = today.replace(day=1)
            self.date_to = today
        elif self.date_range == 'last_month':
            first_this_month = today.replace(day=1)
            last_month_end = first_this_month - timedelta(days=1)
            self.date_from = last_month_end.replace(day=1)
            self.date_to = last_month_end
        elif self.date_range == 'last_quarter':
            current_quarter = (today.month - 1) // 3
            if current_quarter == 0:
                self.date_from = date(today.year - 1, 10, 1)
                self.date_to = date(today.year - 1, 12, 31)
            else:
                start_month = (current_quarter - 1) * 3 + 1
                end_month = current_quarter * 3
                self.date_from = date(today.year, start_month, 1)
                end_date = date(today.year, end_month, 1) + relativedelta(months=1) - timedelta(days=1)
                self.date_to = end_date
        elif self.date_range == 'last_year':
            self.date_from = date(today.year - 1, 1, 1)
            self.date_to = date(today.year - 1, 12, 31)

    def action_create_request(self):
        """Crea la solicitud de descarga y la envía al SAT."""
        self.ensure_one()
        request = self.env['sat.download.request'].create({
            'company_id': self.company_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'download_type': self.download_type,
            'request_type': self.request_type,
            'voucher_type': self.voucher_type,
        })
        request.action_send_request()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sat.download.request',
            'res_id': request.id,
            'view_mode': 'form',
        }
