# -*- coding: utf-8 -*-
import base64
import logging
import os
import re
from datetime import timedelta
from odoo import _, fields
from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal
from .utils import clean as _clean_val, is_valid_email as _is_valid_email_util

_logger = logging.getLogger(__name__)


class MedicineDepotPortal(CustomerPortal):
    """Extiende el Portal del Cliente para alimentar el dashboard Bento."""

    # ------------------------------------------------------------------
    # Rate limit de /afiliacion (POST)
    # ------------------------------------------------------------------
    # DB-backed (modelo medicine.depot.affiliation.attempt): un contador en
    # memoria de proceso NO sirve aqui porque config/odoo.conf corre con
    # `workers = 5` — se probo empiricamente el 2026-07-27 y los requests se
    # reparten entre procesos distintos, por lo que ningun contador en
    # memoria por-worker llega a acumular el limite real. Persistiendo en
    # Postgres, los 5 workers comparten el mismo conteo.
    _AFFILIATION_RATE_LIMIT_WINDOW_SECONDS = 15 * 60
    _AFFILIATION_RATE_LIMIT_MAX_ATTEMPTS = 5

    def _get_request_ip(self):
        return request.httprequest.remote_addr or 'unknown'

    def _is_affiliation_rate_limited(self, ip):
        """True si `ip` ya alcanzo el maximo de intentos en la ventana actual.

        Registra el intento actual como efecto colateral (cuenta para el
        limite independientemente del resultado final del POST). El conteo
        vive en Postgres (`medicine.depot.affiliation.attempt`), compartido
        por los 5 workers de Odoo.
        """
        Attempt = request.env['medicine.depot.affiliation.attempt'].sudo()
        window_start = fields.Datetime.now() - timedelta(
            seconds=self._AFFILIATION_RATE_LIMIT_WINDOW_SECONDS
        )
        attempt_count = Attempt.search_count([
            ('ip_address', '=', ip),
            ('create_date', '>=', window_start),
        ])

        if attempt_count >= self._AFFILIATION_RATE_LIMIT_MAX_ATTEMPTS:
            return True

        Attempt.create({'ip_address': ip})
        return False

    _AFFILIATION_REQUIRED_DOCUMENTS = (
        ('x_studio_operation_notice', 'Aviso de Funcionamiento'),
        ('x_studio_sanitary_license', 'Licencia Sanitaria'),
        ('x_studio_sanitary_responsible_notice', 'Aviso de Responsable Sanitario'),
        ('x_studio_ine', 'INE'),
        ('x_studio_proof_of_address', 'Comprobante de domicilio'),
        ('x_studio_professional_license', 'Cédula profesional'),
        ('x_studio_tax_status_certificate', 'Constancia de situación fiscal'),
    )
    _AFFILIATION_BINARY_FIELDS = tuple(
        field_name for field_name, _label in _AFFILIATION_REQUIRED_DOCUMENTS
    )
    _PORTAL_ACCOUNT_SELECTION_FIELDS = (
        'x_studio_contact_type',
        'x_studio_branch_office',
        'x_studio_person_type',
    )
    _PORTAL_ACCOUNT_ALERT_FIELDS = (
        'x_studio_ine',
        'x_studio_tax_status_certificate',
        'x_studio_operation_notice',
    )
    _AFFILIATION_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
    _AFFILIATION_ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
    _AFFILIATION_ALLOWED_MIME_TYPES = {
        'application/pdf',
        'image/jpeg',
        'image/png',
    }

    # ------------------------------------------------------------------
    # _prepare_home_portal_values
    # ------------------------------------------------------------------
    # IMPORTANTE: este método es invocado por DOS rutas distintas en
    # Odoo 19:
    #   1. GET /my/home  → render completo de la página
    #   2. GET/JSON /my/document_count  → actualización AJAX de contadores
    #
    # En el caso AJAX, el JS itera sobre TODAS las claves devueltas e
    # intenta localizar [data-placeholder-count="<clave>"] en el DOM.
    # Si devolvemos claves como "orders_count", "active_order", etc.,
    # el querySelector devuelve null → TypeError en portal.js.
    #
    # Solución: este método devuelve ÚNICAMENTE el marcador de idioma
    # (stock_label) que es inofensivo; el resto de los valores del bento
    # se añaden en home() justo antes de renderizar, sin pasar por AJAX.
    # ------------------------------------------------------------------

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        values['stock_label'] = _("A la mano")
        return values

    def _get_portal_account_missing_docs_flag(self, partner):
        """Bandera booleana para la alerta del expediente en /my/account."""
        if not partner:
            return False

        partner = partner.sudo()
        model_fields = partner._fields
        return any(
            field_name in model_fields and not partner[field_name]
            for field_name in self._PORTAL_ACCOUNT_ALERT_FIELDS
        )

    def _build_upload_vals(self, model_or_instance):
        """Construye binarios validados de archivos multipart para cualquier contexto de afiliación.

        Acepta tanto el modelo (``res.partner.sudo()``) como un recordset de partner;
        ambos exponen ``._fields`` con la misma interfaz.
        """
        model_fields = model_or_instance._fields
        files = request.httprequest.files
        vals = {}
        errors = []
        for field_name in self._AFFILIATION_BINARY_FIELDS:
            if field_name not in model_fields:
                continue

            upload = files.get(field_name)
            if not upload or not upload.filename:
                continue

            filename = upload.filename
            extension = os.path.splitext(filename)[1].lower()
            content_type = (upload.content_type or '').split(';', 1)[0].strip().lower()
            payload = upload.read()
            upload.stream.seek(0)
            size = len(payload or b'')

            if extension not in self._AFFILIATION_ALLOWED_EXTENSIONS:
                errors.append(_('Archivo no permitido: %(name)s', name=filename))
                continue
            if content_type and content_type not in self._AFFILIATION_ALLOWED_MIME_TYPES:
                errors.append(_('Tipo MIME no permitido: %(name)s', name=filename))
                continue
            if size == 0:
                errors.append(_('Archivo vacío: %(name)s', name=filename))
                continue
            if size > self._AFFILIATION_MAX_FILE_SIZE_BYTES:
                errors.append(_('Archivo excede 5 MB: %(name)s', name=filename))
                continue

            vals[field_name] = base64.b64encode(payload).decode()
            filename_field = f'{field_name}_filename'
            if filename_field in model_fields:
                vals[filename_field] = filename

        return vals, errors

    def _get_portal_account_upload_vals(self, partner):
        return self._build_upload_vals(partner)

    def _get_affiliation_upload_vals(self, partner_model):
        return self._build_upload_vals(partner_model)

    def _get_portal_account_selection_vals(self, partner, post):
        """Construye valores de campos selection Studio del portal."""
        model_fields = partner._fields
        vals = {}
        for field_name in self._PORTAL_ACCOUNT_SELECTION_FIELDS:
            if field_name not in model_fields or field_name not in post:
                continue
            vals[field_name] = (post.get(field_name) or '').strip()
        return vals

    def _is_valid_email(self, email):
        """Valida formato de email; delega a utils.is_valid_email que usa tools.email_normalize."""
        return _is_valid_email_util(email)

    def _validate_affiliation_post(self, post):
        required = {
            'nombre': _('El nombre es obligatorio.'),
            'email': _('El correo profesional es obligatorio.'),
            'telefono': _('El teléfono es obligatorio.'),
            'especialidad': _('La especialidad o giro es obligatoria.'),
        }
        errors = []
        for key, message in required.items():
            if not (post.get(key) or '').strip():
                errors.append(message)

        email = (post.get('email') or '').strip()
        if email and not self._is_valid_email(email):
            errors.append(_('El correo profesional no tiene un formato válido.'))

        if not post.get('privacy'):
            errors.append(_('Debes aceptar el aviso de privacidad para continuar.'))
        return errors

    def _get_affiliation_state(self, partner):
        """Calcula estado de afiliación y faltantes documentales del partner."""
        if not partner:
            return {
                'is_affiliate': False,
                'missing_docs': [],
                'has_missing_docs': False,
                'missing_docs_count': 0,
                'affiliation_upload_url': '/my/account',
            }

        partner = partner.sudo()
        model_fields = partner._fields
        contact_type = (partner.x_studio_contact_type or '').strip() if 'x_studio_contact_type' in model_fields else ''
        is_affiliate = contact_type.lower() == 'cliente'

        missing_docs = []
        if is_affiliate:
            for field_name, label in self._AFFILIATION_REQUIRED_DOCUMENTS:
                if field_name in model_fields and not partner[field_name]:
                    missing_docs.append({
                        'field_name': field_name,
                        'label': _(label),
                    })

        return {
            'is_affiliate': is_affiliate,
            'missing_docs': missing_docs,
            'has_missing_docs': bool(missing_docs),
            'missing_docs_count': len(missing_docs),
            'affiliation_upload_url': '/my/account',
        }

    def _get_bento_portal_values(self):
        """Valores de plantilla para el dashboard Bento.

        Se calculan exclusivamente al renderizar /my/home (no en AJAX).
        No se añaden a _prepare_home_portal_values para evitar que el JS
        nativo los trate como nombres de contadores de documentos.
        """
        partner = request.env.user.partner_id

        SaleOrder = request.env["sale.order"].sudo()
        AccountMove = request.env["account.move"].sudo()
        SaleOrderLine = request.env["sale.order.line"].sudo()

        confirmed_orders = SaleOrder.search(
            [("partner_id", "=", partner.id), ("state", "in", ("sale", "done"))],
            order="date_order desc",
        )
        active_order = confirmed_orders[:1]
        quotes = SaleOrder.search([
            ("partner_id", "=", partner.id),
            ("state", "in", ("draft", "sent")),
        ])
        pending_invoices = AccountMove.search([
            ("partner_id", "=", partner.id),
            ("move_type", "=", "out_invoice"),
            ("payment_state", "in", ("not_paid", "partial")),
            ("state", "=", "posted"),
        ])
        Picking = request.env["stock.picking"].sudo()
        active_pickings = Picking.search([
            ("partner_id", "=", partner.id),
            ("state", "in", ("assigned", "waiting", "confirmed")),
        ])

        top_line_groups = SaleOrderLine._read_group(
            domain=[("order_id.partner_id", "=", partner.id), ("product_id", "!=", False)],
            groupby=["product_id"],
            aggregates=["product_uom_qty:sum"],
        )
        top_line_groups = sorted(
            top_line_groups,
            key=lambda row: row[1] or 0.0,
            reverse=True,
        )[:6]
        favorite_products = []
        for product_group, times_ordered in top_line_groups:
            product = product_group.exists()
            if not product:
                continue
            qty_on_hand = product.qty_available
            favorite_products.append({
                "product": product,
                "times_ordered": times_ordered or 0.0,
                "a_la_mano": qty_on_hand,
                "a_la_mano_label": _("A la mano"),
            })

        recent_orders = SaleOrder.search(
            [("partner_id", "=", partner.id)],
            order="date_order desc",
            limit=5,
        )

        values = {
            "active_order": active_order,
            "orders_count": len(confirmed_orders),
            "last_order": active_order,
            "quotes_count": len(quotes),
            "pickings_count": len(active_pickings),
            "pending_invoices_count": len(pending_invoices),
            "pending_invoices_total": sum(pending_invoices.mapped("amount_residual")),
            "favorite_products": favorite_products,
            "recent_orders": recent_orders,
            "stock_label": _("A la mano"),
        }
        values.update(self._get_affiliation_state(partner))
        return values

    @route(['/my', '/my/home', '/my/dashboard', '/my/bento'], type='http', auth='user', website=True)
    def home(self, **kw):
        """Portal home: añade valores del bento DESPUÉS de super() para
        que /my/document_count (AJAX) nunca reciba claves ajenas a los
        contadores nativos de Odoo.
        """
        response = super().home(**kw)
        if hasattr(response, 'qcontext'):
            response.qcontext.update(self._get_bento_portal_values())
        return response

    @route()
    def account(self, redirect=None, **post):
        """Extiende /my/account para manejar fields Studio + alerta de expediente."""
        partner = request.env.user.partner_id.sudo()
        response = super().account(redirect=redirect, **post)

        if request.httprequest.method == 'POST':
            has_errors = bool(response.qcontext.get('error')) if hasattr(response, 'qcontext') else False
            if not has_errors:
                partner_vals = self._get_portal_account_selection_vals(partner, post)
                upload_vals, upload_errors = self._get_portal_account_upload_vals(partner)
                partner_vals.update(upload_vals)
                if partner_vals:
                    partner.write(partner_vals)

        if hasattr(response, 'qcontext'):
            response.qcontext.update({
                'missing_docs': self._get_portal_account_missing_docs_flag(partner),
                'contact_type_options': self._get_selection_options('x_studio_contact_type'),
                'person_type_options': self._get_selection_options('x_studio_person_type'),
                'branch_office_options': self._get_branch_office_options(),
                'selected_branch_office': self._get_branch_office_selected_value(partner),
            })
        return response

    # ------------------------------------------------------------------
    # /afiliacion
    # ------------------------------------------------------------------

    def _get_selection_options(self, field_name):
        """Obtiene opciones de un campo selection de res.partner."""
        partner_model = request.env['res.partner'].sudo()
        field = partner_model._fields.get(field_name)
        if not field or field.type != 'selection':
            return []

        selection = field.selection
        if callable(selection):
            selection = selection(partner_model)
        return list(selection or [])

    def _get_branch_office_options(self):
        """Opciones de sucursal priorizando stock.warehouse."""
        partner_model = request.env['res.partner'].sudo()
        field = partner_model._fields.get('x_studio_branch_office')
        if not field:
            return []

        warehouses = request.env['stock.warehouse'].sudo().search([('active', '=', True)])
        warehouse_names = [w.display_name for w in warehouses if w.display_name]

        # many2one directo a warehouse: enviar id como value.
        if field.type == 'many2one' and getattr(field, 'comodel_name', '') == 'stock.warehouse':
            return [(str(w.id), w.display_name) for w in warehouses]

        # char/text: persistir nombre de sucursal.
        if field.type in ('char', 'text'):
            return [(name, name) for name in warehouse_names]

        # selection: solo usar values válidos del selection.
        selection_options = self._get_selection_options('x_studio_branch_office')
        if field.type != 'selection':
            return selection_options

        if not warehouse_names:
            return selection_options

        selected = []
        used_values = set()
        for wh_name in warehouse_names:
            wh_norm = wh_name.strip().lower()
            match = next(
                (
                    (value, label)
                    for value, label in selection_options
                    if (str(label or '').strip().lower() == wh_norm)
                    or (str(value or '').strip().lower() == wh_norm)
                ),
                None,
            )
            if match and match[0] not in used_values:
                selected.append(match)
                used_values.add(match[0])

        # Si no hay match entre warehouse y selection, conservar configuración Studio.
        return selected or selection_options

    def _get_branch_office_selected_value(self, partner):
        """Valor escalar comparable contra las opciones del select de sucursal."""
        if not partner or 'x_studio_branch_office' not in partner._fields:
            return ''

        field = partner._fields['x_studio_branch_office']
        value = partner.sudo().x_studio_branch_office
        if not value:
            return ''

        if field.type == 'many2one':
            return str(value.id)

        return value

    def _prepare_afiliacion_qcontext(self):
        """Contexto para renderizar el formulario de afiliación."""
        user = request.env.user
        partner = False
        if user and not user._is_public():
            partner = user.partner_id.sudo()

        values = {
            'partner': partner,
            'contact_type_options': self._get_selection_options('x_studio_contact_type'),
            'person_type_options': self._get_selection_options('x_studio_person_type'),
            'branch_office_options': self._get_branch_office_options(),
            'selected_branch_office': self._get_branch_office_selected_value(partner),
        }
        values.update(self._get_affiliation_state(partner))
        return values

    @route(['/afiliacion'], type='http', auth='public', website=True, methods=['GET', 'POST'])
    def afiliacion(self, **post):
        """Página de afiliación profesional (layout Bento + Studio fields)."""
        if request.httprequest.method != 'POST':
            return request.render(
                'medicine_depot_portal.afiliacion_page',
                self._prepare_afiliacion_qcontext(),
            )

        ip_address = self._get_request_ip()
        if self._is_affiliation_rate_limited(ip_address):
            _logger.warning(
                'Afiliacion: rate limit alcanzado para IP %s (%s intentos / %s min)',
                ip_address,
                self._AFFILIATION_RATE_LIMIT_MAX_ATTEMPTS,
                self._AFFILIATION_RATE_LIMIT_WINDOW_SECONDS // 60,
            )
            return request.make_json_response({
                'success': False,
                'message': _('Demasiados intentos. Por favor espera unos minutos e inténtalo de nuevo.'),
            }, status=429)

        user = request.env.user
        if user and not user._is_public():
            affiliate_state = self._get_affiliation_state(user.partner_id)
            if affiliate_state.get('is_affiliate'):
                return request.make_json_response({
                    'success': False,
                    'message': _('Tu cuenta ya está afiliada.'),
                })

        partner_model = request.env['res.partner'].sudo()
        model_fields = partner_model._fields
        validation_errors = self._validate_affiliation_post(post)
        if validation_errors:
            return request.make_json_response(
                {'success': False, 'message': ' '.join(validation_errors)},
                status=400,
            )

        def _clean(key):
            return _clean_val(post, key)

        def _assign_if_exists(values, field_name, value):
            if field_name in model_fields:
                values[field_name] = value

        partner_vals = {}
        _assign_if_exists(partner_vals, 'name', _clean('nombre'))
        _assign_if_exists(partner_vals, 'email', _clean('email'))
        _assign_if_exists(partner_vals, 'phone', _clean('telefono'))
        _assign_if_exists(partner_vals, 'function', _clean('especialidad'))

        for field_name in (
            'x_studio_contact_type',
            'x_studio_person_type',
            'x_studio_branch_office',
        ):
            _assign_if_exists(partner_vals, field_name, _clean(field_name))

        # Adaptar sucursal al tipo real del campo Studio.
        branch_field = model_fields.get('x_studio_branch_office')
        if branch_field and 'x_studio_branch_office' in partner_vals:
            raw_branch = partner_vals.get('x_studio_branch_office') or ''
            if branch_field.type == 'many2one' and getattr(branch_field, 'comodel_name', '') == 'stock.warehouse':
                partner_vals['x_studio_branch_office'] = int(raw_branch) if raw_branch.isdigit() else False

        # Buscar partner a actualizar:
        # 1) partner del usuario logueado (si aplica)
        # 2) creación de nuevo partner para usuario público
        partner = False
        if user and not user._is_public():
            partner = user.partner_id.sudo()
        else:
            email_to_check = partner_vals.get('email', '')
            if email_to_check:
                existing = partner_model.search([('email', '=', email_to_check)], limit=1)
                if existing:
                    return request.make_json_response({
                        'success': False,
                        'message': _('Ya existe una cuenta con ese correo. Por favor inicia sesión.'),
                    }, status=409)
        upload_vals, upload_errors = self._get_affiliation_upload_vals(partner_model)
        if upload_errors:
            return request.make_json_response(
                {'success': False, 'message': ' '.join(upload_errors)},
                status=400,
            )
        partner_vals.update(upload_vals)
        # Estandarización de datos de afiliación antes de persistir.
        if 'name' in model_fields:
            partner_vals['name'] = (partner_vals.get('name') or '').strip().upper()
        if 'lang' in model_fields:
            partner_vals['lang'] = 'es_MX'
        if 'customer_rank' in model_fields:
            existing_rank = partner.customer_rank if partner and 'customer_rank' in partner._fields else 0
            partner_vals['customer_rank'] = max(existing_rank or 0, 1)
        if 'is_customer' in model_fields:
            partner_vals['is_customer'] = True
        if 'company_type' in model_fields:
            person_type = (partner_vals.get('x_studio_person_type') or '').strip().lower()
            is_company = any(token in person_type for token in ('moral', 'empresa', 'company'))
            partner_vals['company_type'] = 'company' if is_company else 'person'
        if 'x_studio_contact_type' in model_fields:
            partner_vals['x_studio_contact_type'] = 'Cliente'

        try:
            if partner:
                partner.write(partner_vals)
                target_partner = partner
            else:
                target_partner = partner_model.create(partner_vals)
        except Exception:
            return request.make_json_response({
                'success': False,
                'message': _('Ocurrió un error inesperado al procesar tu solicitud.'),
            }, status=500)

        # Evidencia de consentimiento (privacy=on, validado en _validate_affiliation_post).
        # Queda en el log del servidor, no en base de datos: es una primera capa de
        # trazabilidad. Persistirlo en un modelo dedicado queda como follow-up
        # (ver docs/OLLAMA_MIGRATION_PLAN.md, hallazgo Medio #6).
        _logger.info(
            'Afiliacion: consentimiento de privacidad aceptado. partner_id=%s email=%s ip=%s user_agent=%s',
            target_partner.id,
            partner_vals.get('email', ''),
            ip_address,
            request.httprequest.headers.get('User-Agent', ''),
        )

        return request.make_json_response({'success': True})
