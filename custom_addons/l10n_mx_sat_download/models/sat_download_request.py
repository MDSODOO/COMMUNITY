# -*- coding: utf-8 -*-
"""
Modelo principal: sat.download.request

Gestiona el ciclo de vida completo de una solicitud de descarga masiva:
    draft → authenticating → requested → verifying → downloading → done / error

El procesamiento se delega a cron jobs para no bloquear la UI en Odoo.sh.
"""
import base64
import logging
from datetime import timedelta

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError

from ..lib import sat_webservice

_logger = logging.getLogger(__name__)

# Mapeo legible de estados del SAT
SAT_REQUEST_STATES = {
    '1': 'Aceptada',
    '2': 'En proceso',
    '3': 'Terminada',
    '4': 'Error',
    '5': 'Rechazada',
    '6': 'Vencida',
}


class SatDownloadRequest(models.Model):
    _name = 'sat.download.request'
    _description = 'Solicitud de Descarga Masiva SAT'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # =========================================================================
    # Campos
    # =========================================================================
    name = fields.Char(
        string="Referencia",
        default=lambda self: _("Nueva Solicitud"),
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        'res.company',
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('authenticating', 'Autenticando'),
            ('requested', 'Solicitado al SAT'),
            ('verifying', 'Verificando'),
            ('downloading', 'Descargando'),
            ('done', 'Completado'),
            ('error', 'Error'),
        ],
        string="Estado",
        default='draft',
        tracking=True,
        readonly=True,
    )

    # --- Parámetros de la solicitud ---
    date_from = fields.Date(
        string="Fecha Inicio",
        required=True,
    )
    date_to = fields.Date(
        string="Fecha Fin",
        required=True,
    )
    download_type = fields.Selection(
        selection=[
            ('received', 'Recibidos'),
            ('issued', 'Emitidos'),
        ],
        string="Tipo de Descarga",
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

    # --- Datos de respuesta del SAT ---
    sat_request_id = fields.Char(
        string="ID Solicitud SAT",
        readonly=True,
        copy=False,
        index=True,
    )
    sat_status_code = fields.Char(
        string="Código Estado SAT",
        readonly=True,
    )
    sat_request_status = fields.Char(
        string="Estado Solicitud SAT",
        readonly=True,
    )
    sat_message = fields.Text(
        string="Mensaje SAT",
        readonly=True,
    )
    sat_num_cfdis = fields.Integer(
        string="Número de CFDIs",
        readonly=True,
    )
    sat_package_ids_text = fields.Text(
        string="IDs de Paquetes",
        readonly=True,
        help="Lista de IDs de paquetes separados por coma.",
    )
    error_message = fields.Text(
        string="Detalle del Error",
        readonly=True,
    )

    # --- Conteo de XMLs y relación ---
    xml_document_ids = fields.One2many(
        'sat.xml.document',
        'download_request_id',
        string="Documentos XML",
    )
    xml_count = fields.Integer(
        string="XMLs Descargados",
        compute='_compute_xml_count',
    )
    verify_attempts = fields.Integer(
        string="Intentos de Verificación",
        default=0,
        readonly=True,
    )

    # =========================================================================
    # Compute
    # =========================================================================
    @api.depends('xml_document_ids')
    def _compute_xml_count(self):
        for rec in self:
            rec.xml_count = len(rec.xml_document_ids)

    # =========================================================================
    # Constrains
    # =========================================================================
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(_(
                    "La fecha de inicio no puede ser posterior a la fecha fin."
                ))

    # =========================================================================
    # CRUD
    # =========================================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("Nueva Solicitud")) == _("Nueva Solicitud"):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'sat.download.request'
                ) or _("Nueva Solicitud")
        return super().create(vals_list)

    # =========================================================================
    # Acciones de botones (UI)
    # =========================================================================
    def action_send_request(self):
        """Botón 'Solicitar Descarga': inicia el flujo asíncrono."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Solo se pueden enviar solicitudes en estado Borrador."))

        self.write({'state': 'authenticating', 'error_message': False})
        # Disparar el procesamiento inmediato vía cron forzado
        self.with_delay_or_cron('_process_authentication')

    def action_retry(self):
        """Botón 'Reintentar': resetea a borrador para reenviar."""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'sat_request_id': False,
            'sat_status_code': False,
            'sat_request_status': False,
            'sat_message': False,
            'sat_num_cfdis': 0,
            'sat_package_ids_text': False,
            'error_message': False,
            'verify_attempts': 0,
        })

    def action_view_xmls(self):
        """Botón para ver los documentos XML descargados."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("XMLs Descargados"),
            'res_model': 'sat.xml.document',
            'view_mode': 'list,form',
            'domain': [('download_request_id', '=', self.id)],
            'context': {'default_download_request_id': self.id},
        }

    # =========================================================================
    # Wrapper para ejecutar con new cursor (seguro en cron)
    # =========================================================================
    def with_delay_or_cron(self, method_name: str):
        """
        Ejecuta el método en un nuevo cursor para aislamiento transaccional.
        Compatible con Odoo.sh sin dependencias externas (queue_job).
        """
        self.env.cr.commit()  # Guardar estado actual
        try:
            getattr(self.with_context(from_cron=True), method_name)()
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            self.write({
                'state': 'error',
                'error_message': str(e),
            })
            self.env.cr.commit()
            _logger.exception(
                "Error en %s para solicitud %s: %s",
                method_name, self.name, e,
            )

    # =========================================================================
    # Métodos de procesamiento (llamados por cron)
    # =========================================================================
    def _process_authentication(self):
        """Paso 1: Autenticar con FIEL y solicitar descarga."""
        self.ensure_one()
        company = self.company_id
        fiel = company._get_fiel_instance()

        # Autenticar
        token = sat_webservice.authenticate(fiel)

        # Solicitar descarga
        fecha_inicio = self.date_from.strftime('%Y-%m-%dT00:00:00')
        fecha_fin = self.date_to.strftime('%Y-%m-%dT23:59:59')

        result = sat_webservice.request_download(
            fiel=fiel,
            token=token,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo_descarga=self.download_type,
            tipo_solicitud=self.request_type,
            tipo_comprobante=self.voucher_type or None,
        )

        id_solicitud = result.get('id_solicitud', '')
        cod_estatus = result.get('cod_estatus', '')

        if cod_estatus != '5000' or not id_solicitud:
            self.write({
                'state': 'error',
                'sat_status_code': cod_estatus,
                'sat_message': result.get('mensaje', ''),
                'error_message': _(
                    "El SAT rechazó la solicitud. Código: %(code)s — %(msg)s",
                    code=cod_estatus,
                    msg=result.get('mensaje', ''),
                ),
            })
            return

        self.write({
            'state': 'requested',
            'sat_request_id': id_solicitud,
            'sat_status_code': cod_estatus,
            'sat_message': result.get('mensaje', ''),
        })
        _logger.info(
            "SAT solicitud creada: %s → ID %s",
            self.name, id_solicitud,
        )

    def _process_verification(self):
        """Paso 2: Verificar estado de la solicitud en el SAT."""
        self.ensure_one()
        if self.state not in ('requested', 'verifying'):
            return

        company = self.company_id
        fiel = company._get_fiel_instance()
        token = sat_webservice.authenticate(fiel)

        result = sat_webservice.verify_download(
            fiel=fiel,
            token=token,
            request_id=self.sat_request_id,
        )

        estado = result.get('estado_solicitud', '')
        paquetes = result.get('paquetes', [])

        vals = {
            'sat_status_code': result.get('cod_estatus', ''),
            'sat_request_status': SAT_REQUEST_STATES.get(estado, estado),
            'sat_message': result.get('mensaje', ''),
            'sat_num_cfdis': int(result.get('numero_cfdis', 0)),
            'sat_package_ids_text': ','.join(paquetes) if paquetes else '',
            'verify_attempts': self.verify_attempts + 1,
        }

        if estado == '3':
            # Terminada → pasar a descargar
            vals['state'] = 'downloading'
            self.write(vals)
            self._process_download(fiel, token, paquetes)
        elif estado in ('4', '5', '6'):
            # Error / Rechazada / Vencida
            vals['state'] = 'error'
            vals['error_message'] = _(
                "Solicitud %(status)s por el SAT.",
                status=SAT_REQUEST_STATES.get(estado, estado),
            )
            self.write(vals)
        else:
            # En proceso → seguir verificando
            vals['state'] = 'verifying'
            self.write(vals)
            if self.verify_attempts > 40:
                self.write({
                    'state': 'error',
                    'error_message': _(
                        "Se superó el límite de intentos de verificación (40). "
                        "La solicitud puede seguir procesándose en el SAT."
                    ),
                })

    def _process_download(self, fiel, token, paquetes: list):
        """Paso 3: Descargar y extraer los paquetes ZIP."""
        self.ensure_one()
        xml_doc_model = self.env['sat.xml.document']
        total_xmls = 0

        for package_id in paquetes:
            try:
                zip_bytes = sat_webservice.download_package(
                    fiel=fiel,
                    token=token,
                    package_id=package_id,
                )
                xmls = sat_webservice.extract_xmls_from_zip(zip_bytes)

                for filename, xml_content in xmls:
                    xml_doc_model._create_from_xml(
                        xml_content=xml_content,
                        filename=filename,
                        download_request_id=self.id,
                        company_id=self.company_id.id,
                    )
                    total_xmls += 1

            except Exception as e:
                _logger.error(
                    "Error descargando paquete %s: %s", package_id, e,
                )
                self.message_post(
                    body=_(
                        "Error al descargar paquete %(pkg)s: %(err)s",
                        pkg=package_id,
                        err=str(e),
                    ),
                )

        self.write({
            'state': 'done',
            'sat_message': _(
                "Descarga completada: %(count)d XMLs procesados.",
                count=total_xmls,
            ),
        })
        _logger.info(
            "Solicitud %s completada: %d XMLs descargados.",
            self.name, total_xmls,
        )

    # =========================================================================
    # CRON: Procesador principal
    # =========================================================================
    @api.model
    def _cron_process_pending_requests(self):
        """
        Cron job que procesa las solicitudes pendientes.

        Ejecuta en lotes pequeños para respetar los timeouts de Odoo.sh:
        - Solicitudes en 'authenticating' → autenticar + solicitar
        - Solicitudes en 'requested'/'verifying' → verificar estado
        """
        _logger.info("CRON SAT: Procesando solicitudes pendientes...")

        # --- Paso 1: Solicitudes que necesitan autenticación ---
        to_auth = self.search(
            [('state', '=', 'authenticating')],
            limit=5,
        )
        for request in to_auth:
            try:
                request._process_authentication()
                self.env.cr.commit()
            except Exception as e:
                self.env.cr.rollback()
                request.write({
                    'state': 'error',
                    'error_message': str(e),
                })
                self.env.cr.commit()
                _logger.exception(
                    "CRON SAT: Error autenticando %s: %s",
                    request.name, e,
                )

        # --- Paso 2: Solicitudes en espera de verificación ---
        to_verify = self.search(
            [('state', 'in', ('requested', 'verifying'))],
            limit=5,
        )
        for request in to_verify:
            try:
                request._process_verification()
                self.env.cr.commit()
            except Exception as e:
                self.env.cr.rollback()
                request.write({
                    'state': 'error',
                    'error_message': str(e),
                })
                self.env.cr.commit()
                _logger.exception(
                    "CRON SAT: Error verificando %s: %s",
                    request.name, e,
                )

        _logger.info("CRON SAT: Ciclo completado.")
