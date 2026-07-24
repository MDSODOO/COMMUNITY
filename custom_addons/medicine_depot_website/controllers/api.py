# -*- coding: utf-8 -*-
import base64
import logging
import re

from odoo import _, http
from odoo.http import request
from odoo.addons.website.controllers.main import Website

_logger = logging.getLogger(__name__)

_MAX_FILE_SIZE = 6 * 1024 * 1024  # 6 MB por archivo
_ALLOWED_MIMETYPES = {'application/pdf', 'image/jpeg', 'image/png'}

_AFILIACION_DOC_FIELDS = (
    ('aviso_funcionamiento', 'Aviso de Funcionamiento'),
    ('alta_hacienda', 'Alta de Hacienda'),
    ('ine', 'INE'),
    ('comprobante_domicilio', 'Comprobante de Domicilio'),
)


def _valid_email(email):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email or ''))


def _get_or_create_tag(name):
    """Busca o crea una etiqueta CRM por nombre exacto. Usa sudo() para acceso público."""
    Tag = request.env['crm.tag'].sudo()
    tag = Tag.search([('name', '=', name)], limit=1)
    if not tag:
        tag = Tag.create({'name': name})
    return tag


class MdWebsiteApi(http.Controller):

    # ── POST /web/afiliacion/submit ──────────────────────────────────────
    @http.route(
        '/web/afiliacion/submit',
        type='http', auth='public', website=True,
        methods=['POST'],
        csrf=False,  # multipart/form-data con usuario no autenticado; sin sesión no hay token CSRF válido
    )
    def afiliacion_submit(self, **post):
        """POST /web/afiliacion/submit — crea oportunidad CRM con documentos adjuntos desde el formulario público."""
        nombre = (post.get('nombre') or '').strip()
        apellido = (post.get('apellido') or '').strip()
        email = (post.get('email') or '').strip()
        telefono = (post.get('telefono') or '').strip()
        sucursal = (post.get('sucursal') or '').strip()

        errors = []
        if not nombre:
            errors.append(_('El nombre es obligatorio.'))
        if not apellido:
            errors.append(_('El apellido es obligatorio.'))
        if not email or not _valid_email(email):
            errors.append(_('Correo electrónico inválido.'))
        if not telefono:
            errors.append(_('El teléfono es obligatorio.'))

        if errors:
            return request.make_json_response(
                {'success': False, 'message': ' '.join(errors)},
                status=400,
            )

        try:
            # Etiqueta CRM
            tag = _get_or_create_tag('Afiliados')

            # Busca stage 'Afiliado*' o usa el primero disponible
            Stage = request.env['crm.stage'].sudo()
            stage = Stage.search([('name', 'ilike', 'Afiliado')], limit=1)
            if not stage:
                stage = Stage.search([], limit=1, order='sequence asc')

            lead_vals = {
                'name': f'Afiliación: {nombre} {apellido}',
                'contact_name': f'{nombre} {apellido}',
                'email_from': email,
                'phone': telefono,
                'description': f'Sucursal solicitada: {sucursal}' if sucursal else '',
                'type': 'opportunity',
                'tag_ids': [tag.id],
            }
            if stage:
                lead_vals['stage_id'] = stage.id

            lead = request.env['crm.lead'].sudo().create(lead_vals)

            # Adjunta archivos subidos al lead
            for field_name, label in _AFILIACION_DOC_FIELDS:
                file_obj = request.httprequest.files.get(field_name)
                if not file_obj or not file_obj.filename:
                    continue
                content = file_obj.read()
                if len(content) > _MAX_FILE_SIZE:
                    _logger.warning(
                        'mdw.afiliacion: archivo muy grande (%s, %d bytes)',
                        field_name, len(content),
                    )
                    continue
                mimetype = file_obj.content_type or 'application/octet-stream'
                if mimetype not in _ALLOWED_MIMETYPES:
                    _logger.warning('mdw.afiliacion: mimetype no permitido (%s)', mimetype)
                    continue
                request.env['ir.attachment'].sudo().create({
                    'name': file_obj.filename or label,
                    'datas': base64.b64encode(content).decode(),
                    'res_model': 'crm.lead',
                    'res_id': lead.id,
                    'mimetype': mimetype,
                })

            return request.make_json_response({
                'success': True,
                'message': _('Solicitud recibida. Te contactaremos pronto.'),
            })

        except Exception:
            _logger.exception('mdw.afiliacion: error al crear lead')
            return request.make_json_response(
                {'success': False, 'message': _('Error interno. Intenta de nuevo más tarde.')},
                status=500,
            )

    # ── POST /web/medicd/submit ──────────────────────────────────────────
    @http.route(
        '/web/medicd/submit',
        type='http', auth='public', website=True,
        methods=['POST'],
        csrf=False,  # multipart/form-data con usuario no autenticado; sin sesión no hay token CSRF válido
    )
    def medicd_submit(self, **post):
        """POST /web/medicd/submit — crea oportunidad CRM para el programa MedicD desde el formulario público."""
        nombre = (post.get('nombre') or '').strip()
        apellido = (post.get('apellido') or '').strip()
        email = (post.get('email') or '').strip()
        telefono = (post.get('telefono') or '').strip()

        errors = []
        if not nombre:
            errors.append(_('El nombre es obligatorio.'))
        if not email or not _valid_email(email):
            errors.append(_('Correo electrónico inválido.'))

        if errors:
            return request.make_json_response(
                {'success': False, 'message': ' '.join(errors)},
                status=400,
            )

        try:
            tag = _get_or_create_tag('MedicD')

            tiene_farmacia = (post.get('tiene_farmacia') or '') == 'si'
            notas = [f'¿Tiene farmacia? {"Sí" if tiene_farmacia else "No"}']

            if tiene_farmacia:
                for campo in ('direccion', 'cp', 'colonia', 'estado'):
                    val = (post.get(campo) or '').strip()
                    if val:
                        notas.append(f'{campo.capitalize()}: {val}')
                tiene_proveedor = (post.get('tiene_proveedor') or '') == 'si'
                if tiene_proveedor:
                    proveedor = (post.get('proveedor') or '').strip()
                    if proveedor:
                        notas.append(f'Proveedor actual: {proveedor}')
                    else:
                        notas.append('¿Tiene proveedor? Sí (sin nombre)')
                else:
                    notas.append('¿Tiene proveedor? No')
            else:
                apertura = (post.get('tiempo_apertura') or '').strip()
                if apertura:
                    notas.append(f'Tiempo estimado de apertura: {apertura}')
                dir_futura = (post.get('direccion_futura') or '').strip()
                if dir_futura:
                    notas.append(f'Dirección futura: {dir_futura}')

            request.env['crm.lead'].sudo().create({
                'name': f'MedicD: {nombre} {apellido}'.strip(),
                'contact_name': f'{nombre} {apellido}'.strip(),
                'email_from': email,
                'phone': telefono,
                'description': '\n'.join(notas),
                'type': 'opportunity',
                'tag_ids': [tag.id],
            })

            return request.make_json_response({
                'success': True,
                'message': _('Solicitud MedicD recibida. Te contactaremos pronto.'),
            })

        except Exception:
            _logger.exception('mdw.medicd: error al crear lead')
            return request.make_json_response(
                {'success': False, 'message': _('Error interno. Intenta de nuevo más tarde.')},
                status=500,
            )


class MdWebsiteAutocomplete(Website):
    """Override to allow cross-origin calls in staging/preview environments."""

    @http.route(
        '/website/snippet/autocomplete',
        type='json',
        auth='public',
        website=True,
        sitemap=False,
        cors='*',
    )
    def autocomplete(self, **kwargs):
        return super().autocomplete(**kwargs)
