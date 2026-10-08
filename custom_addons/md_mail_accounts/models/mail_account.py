import base64
import imaplib
import smtplib
import logging
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from email.header import decode_header
from email.message import Message
from email import message_from_bytes

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)

SERVER_DEFAULT = 'mail.medicinedepotsureste.mx'


class MdMailAccount(models.Model):
    _name = 'md.mail.account'
    _description = 'Cuenta de Correo por Usuario (IMAP/SMTP)'
    _rec_name = 'imap_user'
    _order = 'user_id'

    user_id = fields.Many2one('res.users', string='Usuario', required=True, ondelete='cascade',
                               default=lambda self: self.env.user)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', related='user_id.company_id', store=True)

    imap_server = fields.Char(string='Servidor IMAP', required=True, default=SERVER_DEFAULT)
    imap_port = fields.Integer(string='Puerto IMAP', required=True, default=993)
    imap_ssl = fields.Boolean(string='Usar SSL', default=True)
    imap_user = fields.Char(string='Usuario IMAP', required=True,
                             default=lambda self: self.env.user.login or '')
    imap_password = fields.Char(string='Contraseña IMAP', required=True)

    smtp_server = fields.Char(string='Servidor SMTP', required=True, default=SERVER_DEFAULT)
    smtp_port = fields.Integer(string='Puerto SMTP', required=True, default=465)
    smtp_encryption = fields.Selection([
        ('ssl', 'SSL/TLS'),
        ('starttls', 'STARTTLS'),
        ('none', 'Sin cifrado'),
    ], string='Cifrado SMTP', default='ssl', required=True)
    smtp_user = fields.Char(string='Usuario SMTP', required=True,
                             default=lambda self: self.env.user.login or '')
    smtp_password = fields.Char(string='Contraseña SMTP')

    last_fetch_date = fields.Datetime(string='Última descarga', readonly=True)
    last_fetch_count = fields.Integer(string='Correos descargados', readonly=True, default=0)
    error_message = fields.Text(string='Último error', readonly=True)
    error_date = fields.Datetime(string='Fecha del error', readonly=True)
    state = fields.Selection([
        ('draft', 'Sin configurar'),
        ('active', 'Activo'),
        ('error', 'Error'),
    ], string='Estado', compute='_compute_state', store=True)

    @api.depends('active', 'error_message')
    def _compute_state(self):
        for rec in self:
            if not rec.active:
                rec.state = 'draft'
            elif rec.error_message:
                rec.state = 'error'
            else:
                rec.state = 'active'

    @api.model
    def _get_default_imap_user(self):
        return self.env.user.login or ''

    @api.onchange('imap_user')
    def _onchange_imap_user(self):
        if self.imap_user and not self.smtp_user:
            self.smtp_user = self.imap_user

    def action_test_imap(self):
        self.ensure_one()
        try:
            conn = self._imap_connect()
            if self.imap_ssl:
                status, folders = conn.list()
            else:
                status, folders = conn.list()
            conn.logout()
            raise UserError(_('Conexión IMAP exitosa.\nBandejas encontradas: %s') %
                            len([f for f in folders if f]))
        except Exception as e:
            raise UserError(_('Error de conexión IMAP:\n%s') % str(e))

    def action_test_smtp(self):
        self.ensure_one()
        try:
            conn = self._smtp_connect()
            conn.quit()
            raise UserError(_('Conexión SMTP exitosa.'))
        except Exception as e:
            raise UserError(_('Error de conexión SMTP:\n%s') % str(e))

    def _imap_connect(self):
        self.ensure_one()
        if self.imap_ssl:
            conn = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        else:
            conn = imaplib.IMAP4(self.imap_server, self.imap_port)
            conn.starttls()
        conn.login(self.imap_user, self.imap_password)
        return conn

    def _smtp_connect(self):
        self.ensure_one()
        password = self.smtp_password or self.imap_password
        if self.smtp_encryption == 'ssl':
            conn = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
        else:
            conn = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.smtp_encryption == 'starttls':
                conn.starttls()
        conn.login(self.smtp_user, password)
        return conn

    def fetch_mails(self):
        self.ensure_one()
        _logger.info('Fetching mail for %s (%s)', self.imap_user, self.user_id.login)
        partner = self.user_id.partner_id
        count = 0
        errors = []
        try:
            conn = self._imap_connect()
            conn.select('INBOX')

            status, search_data = conn.search(None, 'UNSEEN')
            if status != 'OK':
                raise Exception('Error searching UNSEEN: %s' % status)

            message_ids = search_data[0].split() if search_data[0] else []
            _logger.info('Found %d unseen messages for %s', len(message_ids), self.imap_user)

            for mid in message_ids:
                try:
                    status, msg_data = conn.fetch(mid, '(RFC822 FLAGS)')
                    if status != 'OK':
                        continue

                    raw_email = msg_data[0][1]
                    email_message = message_from_bytes(raw_email)

                    mail_values = self._email_to_mail_values(email_message, partner)
                    if mail_values:
                        existing = self.env['mail.mail'].search([
                            ('message_id', '=', mail_values.get('message_id')),
                        ], limit=1)
                        if not existing:
                            mail = self.env['mail.mail'].with_context(
                                mail_create_nosubscribe=True,
                                notify=False,
                            ).create(mail_values)
                            count += 1
                            self._create_attachments(email_message, mail)

                    conn.store(mid, '+FLAGS', '\\Seen')
                except Exception as e:
                    errors.append('MSG %s: %s' % (mid, str(e)))
                    _logger.warning('Error processing message %s for %s: %s',
                                    mid, self.imap_user, e)

            conn.logout()

            self.write({
                'last_fetch_date': fields.Datetime.now(),
                'last_fetch_count': count,
                'error_message': '\n'.join(errors) if errors else False,
                'error_date': fields.Datetime.now() if errors else False,
            })
            _logger.info('Fetched %d mails for %s (%d errors)',
                         count, self.imap_user, len(errors))
        except Exception as e:
            self.write({
                'error_message': str(e),
                'error_date': fields.Datetime.now(),
            })
            _logger.error('IMAP fetch failed for %s: %s', self.imap_user, e)

        return count

    def _resolve_sender_partner(self, email_from):
        addr = email_from
        m = re.search(r'<([^>]+)>', email_from)
        if m:
            addr = m.group(1)
        addr = addr.strip().lower()
        partner = self.env['res.partner'].search([('email', '=ilike', addr)], limit=1)
        if partner:
            return partner
        name_part = email_from.split('<')[0].strip().strip('"\'')
        if name_part and addr and '@' in addr:
            partner = self.env['res.partner'].create({
                'name': name_part,
                'email': addr,
                'is_company': False,
            })
            return partner
        return self.env.ref('base.partner_root')

    def _email_to_mail_values(self, email_message, partner):
        subject = self._decode_header_str(email_message['Subject']) or '(sin asunto)'
        email_from = email_message['From'] or ''
        email_to = email_message['To'] or ''
        date_str = email_message['Date']
        message_id = email_message['Message-ID'] or self._generate_message_id(email_message)

        body_html = self._get_body_html(email_message)

        if not body_html:
            return None

        try:
            date = parsedate_to_datetime(date_str) if date_str else fields.Datetime.now()
        except Exception:
            date = fields.Datetime.now()

        to_partners = self.env['res.partner'].search([
            '|', ('email', '=', email_to),
                 ('email', '=', re.sub(r'.*<([^>]+)>', r'\1', email_to).strip()),
        ], limit=1)
        sender_partner = self._resolve_sender_partner(email_from)

        return {
            'subject': subject,
            'email_from': email_from,
            'email_to': email_to,
            'body_html': body_html,
            'state': 'received',
            'date': date,
            'message_id': message_id,
            'author_id': sender_partner.id,
            'recipient_ids': [(4, p.id) for p in to_partners] if to_partners else [(4, partner.id)],
            'partner_ids': [(4, partner.id)],
        }

    def _decode_header_str(self, value):
        if not value:
            return ''
        try:
            parts = decode_header(value)
            return ''.join([
                part.decode(charset or 'utf-8', errors='replace') if isinstance(part, bytes)
                else (part or '')
                for part, charset in parts
            ])
        except Exception:
            return str(value)

    def _get_body_html(self, email_message):
        if email_message.is_multipart():
            html_part = None
            text_part = None
            for part in email_message.walk():
                ctype = part.get_content_type()
                if ctype == 'text/html' and not html_part:
                    html_part = part
                elif ctype == 'text/plain' and not text_part:
                    text_part = part
                if html_part:
                    break
            payload = html_part or text_part
        else:
            payload = email_message

        if not payload:
            return None

        try:
            raw = payload.get_payload(decode=True)
            charset = payload.get_content_charset() or 'utf-8'
            content = raw.decode(charset, errors='replace')
        except Exception:
            return None

        if payload.get_content_type() == 'text/plain':
            content = '<pre style="font-family:inherit;white-space:pre-wrap">%s</pre>' % content

        return content

    def _create_attachments(self, email_message, mail):
        """Extrae los adjuntos del mensaje (XML/PDF/ZIP de facturas, etc.) y los
        liga al mail.mail ya creado. Antes de este fix, _get_body_html() solo
        tomaba text/html o text/plain y cualquier adjunto se descartaba en
        silencio durante el fetch — nunca llegaba a ir.attachment."""
        if not email_message.is_multipart():
            return
        Attachment = self.env['ir.attachment']
        attachment_ids = []
        for part in email_message.walk():
            if part.is_multipart():
                continue
            filename = part.get_filename()
            if not filename:
                continue
            try:
                filename = self._decode_header_str(filename)
            except Exception:
                pass
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            try:
                attachment = Attachment.create({
                    'name': filename,
                    'datas': base64.b64encode(payload),
                    'res_model': 'mail.mail',
                    'res_id': mail.id,
                    'mimetype': part.get_content_type(),
                })
                attachment_ids.append(attachment.id)
            except Exception as e:
                _logger.warning('Error al crear adjunto %r para mail %s (%s): %s',
                                filename, mail.id, self.imap_user, e)
        if attachment_ids:
            mail.write({'attachment_ids': [(6, 0, attachment_ids)]})

    def _generate_message_id(self, email_message):
        import hashlib
        raw = str(email_message)
        h = hashlib.md5(raw.encode()).hexdigest()
        return '<odoo-md-%s@medicinedepotsureste.mx>' % h

    @api.model
    def _cron_fetch_all(self):
        accounts = self.search([('active', '=', True), ('imap_password', '!=', False)])
        total = 0
        for account in accounts:
            try:
                total += account.fetch_mails()
            except Exception as e:
                _logger.error('CRON fetch all — error on %s: %s', account.imap_user, e)
        _logger.info('CRON fetch all — total mails fetched: %d', total)
        return total

    @api.model
    def _cron_cleanup_old_errors(self):
        cutoff = fields.Datetime.now() - timedelta(days=7)
        old = self.search([('error_date', '<', cutoff), ('error_message', '!=', False)])
        old.write({'error_message': False, 'error_date': False})
        _logger.info('Cleaned %d old error messages', len(old))

    def action_clear_error(self):
        self.write({'error_message': False, 'error_date': False})
