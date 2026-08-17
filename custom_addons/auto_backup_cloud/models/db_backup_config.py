# -*- coding: utf-8 -*-
import base64
import json
import logging
import os
import posixpath
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta

import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import odoo.release
import odoo.tools
import odoo.service.db as sdb
from odoo.tools import osutil

_logger = logging.getLogger(__name__)

# JWT / Cryptography imports for Service Account auth
try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

# Paramiko for SFTP
try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False


class DbBackupConfig(models.Model):
    _name = 'db.backup.config'
    _description = 'Configuración de Respaldos de Base de Datos'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nombre de Configuración', default='Configuración Principal de Respaldo', required=True)
    active = fields.Boolean(string='Activo', default=True)
    db_name = fields.Char(string='Base de Datos Activa', compute='_compute_db_name', readonly=True)

    backup_format = fields.Selection(
        [
            ('zip', 'ZIP con Filestore (Recomendado)'),
            ('dump', 'Dump SQL Comprimido (pg_dump custom format)'),
        ],
        string='Formato de Respaldo',
        default='zip',
        required=True,
        tracking=True,
        help="ZIP incluye tanto el volcado SQL como todos los archivos adjuntos (filestore).",
    )
    with_filestore = fields.Boolean(
        string='Incluir Filestore',
        default=True,
        help="Si se desmarca, el archivo ZIP contendrá solo el volcado de la base de datos sin adjuntos.",
    )

    # ─────────────────────────────────────────────────────────────
    # Destino 1: Almacenamiento Local
    # ─────────────────────────────────────────────────────────────
    local_backup_active = fields.Boolean(string='Guardar Copia Local en Servidor', default=True, tracking=True)
    local_backup_dir = fields.Char(
        string='Directorio Local de Respaldos',
        default='/var/lib/odoo/backups',
        help="Ruta absoluta en el servidor donde se almacenarán las copias locales.",
    )
    retention_type = fields.Selection(
        [
            ('days', 'Por Días de Antigüedad'),
            ('count', 'Por Número de Respaldos Recientes'),
        ],
        string='Política de Retención Local',
        default='days',
        required=True,
    )
    retention_days = fields.Integer(string='Días a Conservar (Local)', default=7)
    retention_count = fields.Integer(string='Máximo de Respaldos a Conservar (Local)', default=10)

    # ─────────────────────────────────────────────────────────────
    # Destino 2: Google Drive
    # ─────────────────────────────────────────────────────────────
    gdrive_active = fields.Boolean(string='Habilitar Respaldo en Google Drive', default=False, tracking=True)
    gdrive_auth_type = fields.Selection(
        [
            ('service_account', 'Service Account (Cuenta de Servicio JSON)'),
            ('oauth', 'OAuth2 (Refresh Token / Client ID / Secret)'),
        ],
        string='Tipo de Autenticación Google',
        default='service_account',
    )
    gdrive_service_account_json = fields.Text(
        string='Credenciales Service Account (JSON)',
        help="Pega aquí el contenido completo del archivo JSON descargado de Google Cloud Console.",
    )
    gdrive_client_id = fields.Char(string='Client ID')
    gdrive_client_secret = fields.Char(string='Client Secret')
    gdrive_refresh_token = fields.Char(string='Refresh Token')
    gdrive_folder_id = fields.Char(
        string='ID de Carpeta en Google Drive',
        help="El identificador de la carpeta destino en Google Drive (extraído de la URL: drive.google.com/drive/folders/ID).",
    )
    gdrive_retention_days = fields.Integer(
        string='Días a Conservar en Google Drive',
        default=14,
        help="0 para desactivar la depuración automática en Google Drive.",
    )

    # ─────────────────────────────────────────────────────────────
    # Destino 3: Servidor Remoto (SFTP / SSH)
    # ─────────────────────────────────────────────────────────────
    sftp_active = fields.Boolean(string='Habilitar Envío a Servidor Remoto (SFTP/SSH)', default=False, tracking=True)
    sftp_host = fields.Char(string='Host / IP del Servidor Remoto')
    sftp_port = fields.Integer(string='Puerto SFTP', default=22)
    sftp_user = fields.Char(string='Usuario SFTP')
    sftp_auth_type = fields.Selection(
        [
            ('password', 'Contraseña'),
            ('key', 'Clave Privada SSH (Recomendado)'),
        ],
        string='Tipo de Autenticación SFTP',
        default='key',
    )
    sftp_password = fields.Char(string='Contraseña SFTP')
    sftp_private_key = fields.Text(
        string='Clave Privada SSH (PEM / OpenSSH)',
        help="Contenido de la clave privada (ej. id_rsa o id_ed25519).",
    )
    sftp_passphrase = fields.Char(string='Frase de Paso de Clave SSH (Opcional)')
    sftp_remote_dir = fields.Char(string='Directorio Remoto de Destino', default='/backups/odoo')
    sftp_retention_days = fields.Integer(
        string='Días a Conservar en Servidor SFTP',
        default=14,
        help="0 para desactivar la depuración automática en el servidor remoto.",
    )

    # ─────────────────────────────────────────────────────────────
    # Programación (Cron) y Estado
    # ─────────────────────────────────────────────────────────────
    cron_id = fields.Many2one('ir.cron', string='Acción Planificada (Cron)', readonly=True)
    cron_active = fields.Boolean(string='Respaldo Automático Programado', compute='_compute_cron_status', inverse='_inverse_cron_status')
    cron_interval_number = fields.Integer(string='Intervalo', default=1)
    cron_interval_type = fields.Selection(
        [
            ('hours', 'Horas'),
            ('days', 'Días'),
            ('weeks', 'Semanas'),
        ],
        string='Unidad de Frecuencia',
        default='days',
    )
    cron_nextcall = fields.Datetime(string='Próxima Ejecución', compute='_compute_cron_status')

    last_backup_date = fields.Datetime(string='Último Respaldo', readonly=True)
    last_backup_status = fields.Selection(
        [
            ('success', 'Exitoso'),
            ('warning', 'Parcial / Con Advertencias'),
            ('error', 'Fallido'),
        ],
        string='Estado del Último Respaldo',
        readonly=True,
    )
    last_backup_log_id = fields.Many2one('db.backup.log', string='Registro del Último Respaldo', readonly=True)
    log_ids = fields.One2many('db.backup.log', 'config_id', string='Historial de Respaldos')
    log_count = fields.Integer(string='Total de Respaldos', compute='_compute_log_count')

    def _compute_db_name(self):
        current_db = self.env.cr.dbname
        for record in self:
            record.db_name = current_db

    def _compute_log_count(self):
        for record in self:
            record.log_count = len(record.log_ids)

    def _compute_cron_status(self):
        for record in self:
            cron = record._get_or_create_cron()
            record.cron_active = cron.active if cron else False
            record.cron_nextcall = cron.nextcall if cron else False

    def _inverse_cron_status(self):
        for record in self:
            cron = record._get_or_create_cron()
            if cron:
                cron.write({
                    'active': record.cron_active,
                    'interval_number': record.cron_interval_number or 1,
                    'interval_type': record.cron_interval_type or 'days',
                })

    def _get_or_create_cron(self):
        self.ensure_one()
        cron = self.env.ref('auto_backup_cloud.ir_cron_auto_backup_cloud', raise_if_not_found=False)
        if not cron:
            cron = self.env['ir.cron'].search([('name', '=', 'Auto Backup Cloud: Respaldo Automático')], limit=1)
        if not cron:
            model_id = self.env['ir.model']._get_id('db.backup.config')
            cron = self.env['ir.cron'].create({
                'name': 'Auto Backup Cloud: Respaldo Automático',
                'model_id': model_id,
                'state': 'code',
                'code': 'model._run_scheduled_backup()',
                'interval_number': self.cron_interval_number or 1,
                'interval_type': self.cron_interval_type or 'days',
                'active': True,
            })
        if self.cron_id != cron:
            self.cron_id = cron
        return cron

    # ─────────────────────────────────────────────────────────────
    # MOTOR DE GOOGLE DRIVE (REST API v3)
    # ─────────────────────────────────────────────────────────────
    def _get_gdrive_access_token(self):
        self.ensure_one()
        if self.gdrive_auth_type == 'service_account':
            if not self.gdrive_service_account_json:
                raise UserError(_("No se han configurado las credenciales JSON de Service Account."))
            try:
                sa_data = json.loads(self.gdrive_service_account_json.strip())
            except Exception as e:
                raise UserError(_("El JSON de Service Account es inválido: %s") % str(e))

            client_email = sa_data.get('client_email')
            private_key_pem = sa_data.get('private_key')
            token_uri = sa_data.get('token_uri', 'https://oauth2.googleapis.com/token')

            if not client_email or not private_key_pem:
                raise UserError(_("El JSON de Service Account debe contener 'client_email' y 'private_key'."))

            if not HAS_CRYPTOGRAPHY:
                raise UserError(_("La librería Python 'cryptography' es requerida para autenticación con Service Account."))

            # Construir y firmar JWT
            now_ts = int(time.time())
            header = {'alg': 'RS256', 'typ': 'JWT'}
            payload = {
                'iss': client_email,
                'scope': 'https://www.googleapis.com/auth/drive',
                'aud': token_uri,
                'exp': now_ts + 3600,
                'iat': now_ts,
            }

            def b64_url(data_bytes):
                return base64.urlsafe_b64encode(data_bytes).decode('utf-8').rstrip('=')

            header_b64 = b64_url(json.dumps(header).encode('utf-8'))
            payload_b64 = b64_url(json.dumps(payload).encode('utf-8'))
            signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')

            private_key = load_pem_private_key(private_key_pem.encode('utf-8'), password=None)
            signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
            signature_b64 = b64_url(signature)

            jwt_token = f"{header_b64}.{payload_b64}.{signature_b64}"

            # Canjear JWT por Access Token
            res = requests.post(
                token_uri,
                data={
                    'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                    'assertion': jwt_token,
                },
                timeout=20,
            )
            if res.status_code != 200:
                raise UserError(_("Error obteniendo token de Google Drive: %s") % res.text)
            return res.json().get('access_token')

        elif self.gdrive_auth_type == 'oauth':
            if not self.gdrive_client_id or not self.gdrive_client_secret or not self.gdrive_refresh_token:
                raise UserError(_("Para autenticación OAuth2 se requiere Client ID, Client Secret y Refresh Token."))

            res = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': self.gdrive_client_id.strip(),
                    'client_secret': self.gdrive_client_secret.strip(),
                    'refresh_token': self.gdrive_refresh_token.strip(),
                    'grant_type': 'refresh_token',
                },
                timeout=20,
            )
            if res.status_code != 200:
                raise UserError(_("Error refrescando token OAuth2 de Google Drive: %s") % res.text)
            return res.json().get('access_token')

        raise UserError(_("Tipo de autenticación Google no soportado."))

    def _test_gdrive_connection(self):
        self.ensure_one()
        token = self._get_gdrive_access_token()
        headers = {'Authorization': f'Bearer {token}'}

        folder_id = (self.gdrive_folder_id or '').strip()
        if folder_id:
            url = f'https://www.googleapis.com/drive/v3/files/{folder_id}?fields=id,name,mimeType,capabilities'
            res = requests.get(url, headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json()
                fname = data.get('name', folder_id)
                can_add = data.get('capabilities', {}).get('canAddChildren', True)
                if not can_add:
                    return False, _("Conectado con éxito a Google Drive, pero no tienes permisos de escritura en la carpeta '%s'.") % fname
                return True, _("¡Conexión exitosa con Google Drive! Carpeta detectada: '%s' (ID: %s)") % (fname, folder_id)
            else:
                return False, _("Error accediendo a la carpeta en Google Drive (%s): %s") % (res.status_code, res.text)
        else:
            url = 'https://www.googleapis.com/drive/v3/about?fields=user'
            res = requests.get(url, headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json()
                email = data.get('user', {}).get('emailAddress', 'Desconocido')
                return True, _("¡Conexión exitosa con Google Drive! Usuario autenticado: %s (Nota: No se configuró ID de carpeta destino, se guardará en la raíz).") % email
            else:
                return False, _("Error consultando información de Google Drive (%s): %s") % (res.status_code, res.text)

    def action_test_gdrive(self):
        self.ensure_one()
        try:
            ok, msg = self._test_gdrive_connection()
            notification_type = 'success' if ok else 'danger'
            title = _("Prueba de Google Drive: Éxito") if ok else _("Prueba de Google Drive: Fallo")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': msg,
                    'type': notification_type,
                    'sticky': True if not ok else False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Error en Prueba de Google Drive"),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def _upload_file_gdrive(self, local_path, filename, log_lines):
        self.ensure_one()
        token = self._get_gdrive_access_token()
        file_size = os.path.getsize(local_path)
        log_lines.append(f"[GDrive] Iniciando subida resumible de '{filename}' ({file_size} bytes)...")

        # 1. Iniciar subida resumible
        init_headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json; charset=UTF-8',
            'X-Upload-Content-Type': 'application/zip' if filename.endswith('.zip') else 'application/octet-stream',
            'X-Upload-Content-Length': str(file_size),
        }
        metadata = {'name': filename}
        if self.gdrive_folder_id and self.gdrive_folder_id.strip():
            metadata['parents'] = [self.gdrive_folder_id.strip()]

        init_url = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable'
        init_res = requests.post(init_url, headers=init_headers, json=metadata, timeout=30)
        if init_res.status_code != 200:
            raise UserError(_("Error iniciando subida a Google Drive (%s): %s") % (init_res.status_code, init_res.text))

        location = init_res.headers.get('Location')
        if not location:
            raise UserError(_("Google Drive no devolvió la URL de carga resumible (Location header)."))

        # 2. Subir por bloques (5 MB por chunk)
        chunk_size = 5 * 1024 * 1024
        uploaded_bytes = 0
        file_id = False

        with open(local_path, 'rb') as f:
            while uploaded_bytes < file_size:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                chunk_len = len(chunk)
                start_byte = uploaded_bytes
                end_byte = uploaded_bytes + chunk_len - 1

                chunk_headers = {
                    'Content-Range': f'bytes {start_byte}-{end_byte}/{file_size}',
                    'Content-Length': str(chunk_len),
                }

                chunk_res = requests.put(location, headers=chunk_headers, data=chunk, timeout=60)
                uploaded_bytes += chunk_len
                pct = (uploaded_bytes / file_size) * 100
                _logger.info("GDrive Upload Progress '%s': %.1f%% (%d/%d bytes)", filename, pct, uploaded_bytes, file_size)

                if chunk_res.status_code in [200, 201]:
                    data = chunk_res.json()
                    file_id = data.get('id')
                    break
                elif chunk_res.status_code == 308:
                    continue
                else:
                    raise UserError(_("Error transfiriendo bloque a Google Drive (%s): %s") % (chunk_res.status_code, chunk_res.text))

        log_lines.append(f"[GDrive] ✓ Subida completada exitosamente. ID en Drive: {file_id}")
        return file_id

    def _purge_gdrive_files(self, log_lines):
        self.ensure_one()
        if not self.gdrive_retention_days or self.gdrive_retention_days <= 0:
            return

        cutoff_date = datetime.utcnow() - timedelta(days=self.gdrive_retention_days)
        cutoff_iso = cutoff_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        token = self._get_gdrive_access_token()
        headers = {'Authorization': f'Bearer {token}'}

        folder_filter = f"'{self.gdrive_folder_id.strip()}' in parents and " if self.gdrive_folder_id and self.gdrive_folder_id.strip() else ""
        query = f"{folder_filter}trashed = false and createdTime < '{cutoff_iso}'"

        url = f"https://www.googleapis.com/drive/v3/files?q={requests.utils.quote(query)}&fields=files(id,name,createdTime)"
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code != 200:
            log_lines.append(f"[GDrive Purge] ⚠ Error listando archivos para depuración: {res.text}")
            return

        files = res.json().get('files', [])
        deleted_count = 0
        for f in files:
            fname = f.get('name', '')
            fid = f.get('id')
            if fname.startswith('backup_') or fname.endswith('.zip') or fname.endswith('.dump'):
                del_res = requests.delete(f"https://www.googleapis.com/drive/v3/files/{fid}", headers=headers, timeout=20)
                if del_res.status_code in [200, 204]:
                    deleted_count += 1
                    log_lines.append(f"[GDrive Purge] Eliminado archivo antiguo: {fname} (ID: {fid})")

        if deleted_count > 0:
            log_lines.append(f"[GDrive Purge] Total de archivos depurados en Drive: {deleted_count}")

    # ─────────────────────────────────────────────────────────────
    # MOTOR SFTP / SERVIDOR REMOTO
    # ─────────────────────────────────────────────────────────────
    def _get_sftp_client(self):
        self.ensure_one()
        if not HAS_PARAMIKO:
            raise UserError(_("La librería Python 'paramiko' es requerida para SFTP/SSH."))

        if not self.sftp_host or not self.sftp_user:
            raise UserError(_("Se requiere especificar Host y Usuario para la conexión SFTP."))

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        port = self.sftp_port or 22
        timeout = 25

        if self.sftp_auth_type == 'key':
            if not self.sftp_private_key:
                raise UserError(_("No se ha configurado la clave privada SSH para la autenticación SFTP."))

            import io
            key_file = io.StringIO(self.sftp_private_key.strip())
            pkey = None
            passphrase = self.sftp_passphrase.strip() if self.sftp_passphrase else None

            key_classes = [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey]
            last_err = None
            for kcls in key_classes:
                try:
                    key_file.seek(0)
                    pkey = kcls.from_private_key(key_file, password=passphrase)
                    break
                except Exception as e:
                    last_err = e

            if not pkey:
                raise UserError(_("No se pudo interpretar la clave privada SSH: %s") % str(last_err))

            ssh.connect(self.sftp_host.strip(), port=port, username=self.sftp_user.strip(), pkey=pkey, timeout=timeout)
        else:
            if not self.sftp_password:
                raise UserError(_("No se ha configurado la contraseña para la autenticación SFTP."))
            ssh.connect(
                self.sftp_host.strip(),
                port=port,
                username=self.sftp_user.strip(),
                password=self.sftp_password,
                timeout=timeout,
            )

        sftp = ssh.open_sftp()
        return ssh, sftp

    def _test_sftp_connection(self):
        self.ensure_one()
        ssh, sftp = None, None
        try:
            ssh, sftp = self._get_sftp_client()
            rdir = (self.sftp_remote_dir or '/backups').strip()

            # Asegurar o verificar directorio remoto
            try:
                sftp.stat(rdir)
            except IOError:
                parts = rdir.strip('/').split('/')
                curr = ''
                for p in parts:
                    curr += '/' + p
                    try:
                        sftp.stat(curr)
                    except IOError:
                        sftp.mkdir(curr)

            # Prueba de escritura/lectura
            probe_file = posixpath.join(rdir, '.odoo_backup_probe')
            with sftp.file(probe_file, 'w') as f:
                f.write(f"probe_{datetime.utcnow().isoformat()}")
            sftp.remove(probe_file)

            return True, _("¡Conexión SFTP exitosa! Host: %s:%s, Directorio verificado y accesible: '%s'") % (
                self.sftp_host, self.sftp_port or 22, rdir
            )
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass
            if ssh:
                try:
                    ssh.close()
                except Exception:
                    pass

    def action_test_sftp(self):
        self.ensure_one()
        try:
            ok, msg = self._test_sftp_connection()
            notification_type = 'success' if ok else 'danger'
            title = _("Prueba SFTP: Éxito") if ok else _("Prueba SFTP: Fallo")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': msg,
                    'type': notification_type,
                    'sticky': True if not ok else False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Error en Prueba SFTP"),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def _upload_file_sftp(self, local_path, filename, log_lines):
        self.ensure_one()
        ssh, sftp = None, None
        try:
            ssh, sftp = self._get_sftp_client()
            rdir = (self.sftp_remote_dir or '/backups').strip()

            parts = rdir.strip('/').split('/')
            curr = ''
            for p in parts:
                curr += '/' + p
                try:
                    sftp.stat(curr)
                except IOError:
                    sftp.mkdir(curr)

            remote_dest = posixpath.join(rdir, filename)
            file_size = os.path.getsize(local_path)
            log_lines.append(f"[SFTP] Iniciando transferencia hacia {self.sftp_host}:{remote_dest} ({file_size} bytes)...")

            sftp.put(local_path, remote_dest)
            log_lines.append(f"[SFTP] ✓ Transferencia completada exitosamente en {remote_dest}")
            return remote_dest
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass
            if ssh:
                try:
                    ssh.close()
                except Exception:
                    pass

    def _purge_sftp_files(self, log_lines):
        self.ensure_one()
        if not self.sftp_retention_days or self.sftp_retention_days <= 0:
            return

        cutoff_ts = time.time() - (self.sftp_retention_days * 86400)
        ssh, sftp = None, None
        try:
            ssh, sftp = self._get_sftp_client()
            rdir = (self.sftp_remote_dir or '/backups').strip()
            entries = sftp.listdir_attr(rdir)
            deleted_count = 0

            for entry in entries:
                fname = entry.filename
                if fname.startswith('backup_') or fname.endswith('.zip') or fname.endswith('.dump'):
                    if entry.st_mtime and entry.st_mtime < cutoff_ts:
                        full_remote = posixpath.join(rdir, fname)
                        sftp.remove(full_remote)
                        deleted_count += 1
                        log_lines.append(f"[SFTP Purge] Eliminado archivo remoto antiguo: {full_remote}")

            if deleted_count > 0:
                log_lines.append(f"[SFTP Purge] Total de archivos depurados en SFTP: {deleted_count}")
        except Exception as e:
            log_lines.append(f"[SFTP Purge] ⚠ Error durante la depuración en SFTP: {str(e)}")
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass
            if ssh:
                try:
                    ssh.close()
                except Exception:
                    pass

    # ─────────────────────────────────────────────────────────────
    # MOTOR DE EXTRACCIÓN DE BASE DE DATOS Y LIMPIEZA LOCAL
    # ─────────────────────────────────────────────────────────────
    def _generate_dump_manifest(self, cr):
        """Genera el manifest.json para el volcado sin depender de @check_db_management_enabled."""
        try:
            pg_version = "%d.%d" % divmod(cr._obj.connection.server_version / 100, 100)
        except Exception:
            pg_version = "15.0"
        cr.execute("SELECT name, latest_version FROM ir_module_module WHERE state = 'installed'")
        modules = dict(cr.fetchall())
        return {
            'odoo_dump': '1',
            'db_name': cr.dbname,
            'version': odoo.release.version,
            'version_info': odoo.release.version_info,
            'major_version': odoo.release.major_version,
            'pg_version': pg_version,
            'modules': modules,
        }

    def _perform_database_dump(self, dest_path, format_type, with_filestore, log_lines):
        self.ensure_one()
        db_name = self.env.cr.dbname
        log_lines.append(f"[Dump Engine] Iniciando volcado de '{db_name}' (formato={format_type}, filestore={with_filestore})...")

        t0 = time.time()
        cmd = [sdb.find_pg_tool('pg_dump'), '--no-owner', db_name]
        env_pg = sdb.exec_pg_environ()

        if format_type == 'zip':
            with tempfile.TemporaryDirectory() as dump_dir:
                if with_filestore:
                    filestore = odoo.tools.config.filestore(db_name)
                    if os.path.exists(filestore):
                        shutil.copytree(filestore, os.path.join(dump_dir, 'filestore'))
                with open(os.path.join(dump_dir, 'manifest.json'), 'w') as fh:
                    manifest = self._generate_dump_manifest(self.env.cr)
                    json.dump(manifest, fh, indent=4)
                cmd.insert(-1, '--file=' + os.path.join(dump_dir, 'dump.sql'))
                subprocess.run(cmd, env=env_pg, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True)
                with open(dest_path, 'wb') as stream:
                    osutil.zip_dir(dump_dir, stream, include_dir=False, fnct_sort=lambda fn: fn != 'dump.sql')
        else:
            cmd.insert(-1, '--format=c')
            with open(dest_path, 'wb') as stream:
                proc = subprocess.Popen(cmd, env=env_pg, stdout=stream, stderr=subprocess.PIPE)
                _, stderr = proc.communicate()
                if proc.returncode != 0:
                    raise UserError(_("Error ejecutando pg_dump: %s") % stderr.decode('utf-8'))

        elapsed = time.time() - t0
        file_size = os.path.getsize(dest_path)
        log_lines.append(f"[Dump Engine] ✓ Volcado finalizado en {elapsed:.2f}s. Tamaño: {file_size} bytes.")

    def _purge_local_files(self, log_lines):
        self.ensure_one()
        ldir = (self.local_backup_dir or '/var/lib/odoo/backups').strip()
        if not os.path.exists(ldir):
            return

        db_prefix = f"backup_{self.env.cr.dbname}_"
        all_backups = []
        for fname in os.listdir(ldir):
            if fname.startswith(db_prefix) and (fname.endswith('.zip') or fname.endswith('.dump')):
                fpath = os.path.join(ldir, fname)
                if os.path.isfile(fpath):
                    all_backups.append((fpath, fname, os.path.getmtime(fpath)))

        deleted = 0
        if self.retention_type == 'days' and self.retention_days > 0:
            cutoff_ts = time.time() - (self.retention_days * 86400)
            for fpath, fname, mtime in all_backups:
                if mtime < cutoff_ts:
                    try:
                        os.remove(fpath)
                        deleted += 1
                        log_lines.append(f"[Local Purge] Eliminado respaldo local antiguo: {fname}")
                    except Exception as e:
                        log_lines.append(f"[Local Purge] ⚠ Error eliminando {fname}: {e}")

        elif self.retention_type == 'count' and self.retention_count > 0:
            all_backups.sort(key=lambda x: x[2], reverse=True)
            to_delete = all_backups[self.retention_count:]
            for fpath, fname, mtime in to_delete:
                try:
                    os.remove(fpath)
                    deleted += 1
                    log_lines.append(f"[Local Purge] Eliminado respaldo local excedente: {fname}")
                except Exception as e:
                    log_lines.append(f"[Local Purge] ⚠ Error eliminando {fname}: {e}")

        if deleted > 0:
            log_lines.append(f"[Local Purge] Total de archivos locales depurados: {deleted}")

    # ─────────────────────────────────────────────────────────────
    # ORQUESTADOR PRINCIPAL (MANUAL Y CRON)
    # ─────────────────────────────────────────────────────────────
    def action_backup_now(self):
        self.ensure_one()
        return self._execute_backup(backup_type='manual')

    @api.model
    def _run_scheduled_backup(self):
        configs = self.search([('active', '=', True)])
        if not configs:
            configs = self.create({'name': 'Configuración Automática de Respaldo'})
        for cfg in configs:
            try:
                cfg._execute_backup(backup_type='cron')
            except Exception as e:
                _logger.error("Error ejecutando respaldo programado en config %s: %s", cfg.id, e, exc_info=True)

    def _execute_backup(self, backup_type='manual'):
        self.ensure_one()
        start_time = datetime.utcnow()
        t0 = time.time()
        db_name = self.env.cr.dbname
        timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        ext = 'zip' if self.backup_format == 'zip' else 'dump'
        filename = f"backup_{db_name}_{timestamp_str}.{ext}"

        log_lines = [
            f"=== INICIANDO RESPALDO DE BASE DE DATOS ===",
            f"Fecha / Hora UTC: {datetime.utcnow().isoformat()}",
            f"Base de datos: {db_name}",
            f"Tipo de ejecución: {backup_type}",
            f"Formato: {self.backup_format} (Filestore: {self.with_filestore if self.backup_format == 'zip' else 'N/A'})",
            f"Archivo destino: {filename}",
            "-" * 50,
        ]

        local_status = 'skipped'
        gdrive_status = 'skipped'
        sftp_status = 'skipped'
        local_final_path = ''
        gdrive_file_id = ''
        sftp_remote_path = ''

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_backup_file = os.path.join(tmp_dir, filename)

            # 1. Realizar volcado
            try:
                self._perform_database_dump(temp_backup_file, self.backup_format, self.with_filestore, log_lines)
                file_size = os.path.getsize(temp_backup_file)
            except Exception as dump_err:
                log_lines.append(f"[FATAL] Falló la extracción de la base de datos: {str(dump_err)}")
                duration = time.time() - t0
                end_time = datetime.utcnow()

                log_rec = self.env['db.backup.log'].sudo().create({
                    'name': filename,
                    'config_id': self.id,
                    'db_name': db_name,
                    'backup_format': self.backup_format,
                    'backup_type': backup_type,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_seconds': duration,
                    'file_size_bytes': 0,
                    'overall_status': 'error',
                    'details': "\n".join(log_lines),
                })
                self.env.cr.commit()
                raise UserError(_("Falló la extracción del respaldo: %s") % str(dump_err))

            # 2. Destino Local
            if self.local_backup_active:
                try:
                    ldir = (self.local_backup_dir or '/var/lib/odoo/backups').strip()
                    os.makedirs(ldir, exist_ok=True)
                    local_final_path = os.path.join(ldir, filename)
                    shutil.copy2(temp_backup_file, local_final_path)
                    local_status = 'success'
                    log_lines.append(f"[Local Storage] ✓ Archivo guardado localmente en: {local_final_path}")
                    self._purge_local_files(log_lines)
                except Exception as loc_err:
                    local_status = 'error'
                    log_lines.append(f"[Local Storage] ❌ Error guardando copia local: {str(loc_err)}")

            # 3. Destino Google Drive
            if self.gdrive_active:
                try:
                    gdrive_file_id = self._upload_file_gdrive(temp_backup_file, filename, log_lines)
                    gdrive_status = 'success'
                    self._purge_gdrive_files(log_lines)
                except Exception as gd_err:
                    gdrive_status = 'error'
                    log_lines.append(f"[GDrive] ❌ Error en subida a Google Drive: {str(gd_err)}")

            # 4. Destino SFTP
            if self.sftp_active:
                try:
                    sftp_remote_path = self._upload_file_sftp(temp_backup_file, filename, log_lines)
                    sftp_status = 'success'
                    self._purge_sftp_files(log_lines)
                except Exception as sftp_err:
                    sftp_status = 'error'
                    log_lines.append(f"[SFTP] ❌ Error en transferencia SFTP: {str(sftp_err)}")

        duration = time.time() - t0
        end_time = datetime.utcnow()
        log_lines.append("-" * 50)
        log_lines.append(f"=== FIN DE RESPALDO (Duración total: {duration:.2f} segundos) ===")

        # Evaluar estado general
        statuses = []
        if self.local_backup_active:
            statuses.append(local_status)
        if self.gdrive_active:
            statuses.append(gdrive_status)
        if self.sftp_active:
            statuses.append(sftp_status)

        if not statuses:
            overall_status = 'warning'
            log_lines.append("⚠ Ningún destino estaba habilitado para almacenar el respaldo.")
        elif all(s == 'success' for s in statuses):
            overall_status = 'success'
        elif any(s == 'success' for s in statuses):
            overall_status = 'warning'
        else:
            overall_status = 'error'

        log_rec = self.env['db.backup.log'].sudo().create({
            'name': filename,
            'config_id': self.id,
            'db_name': db_name,
            'backup_format': self.backup_format,
            'backup_type': backup_type,
            'start_time': start_time,
            'end_time': end_time,
            'duration_seconds': duration,
            'file_size_bytes': file_size,
            'local_status': local_status,
            'local_path': local_final_path,
            'gdrive_status': gdrive_status,
            'gdrive_file_id': gdrive_file_id,
            'sftp_status': sftp_status,
            'sftp_remote_path': sftp_remote_path,
            'overall_status': overall_status,
            'details': "\n".join(log_lines),
        })

        self.sudo().write({
            'last_backup_date': end_time,
            'last_backup_status': overall_status,
            'last_backup_log_id': log_rec.id,
        })
        self.env.cr.commit()

        if backup_type == 'manual':
            title = _("Respaldo Completado con Éxito") if overall_status == 'success' else _("Respaldo con Advertencias / Errores")
            ntype = 'success' if overall_status == 'success' else ('warning' if overall_status == 'warning' else 'danger')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': _("Respaldo '%s' generado (%s). Revisa los detalles en el registro de auditoría.") % (filename, log_rec.file_size_human),
                    'type': ntype,
                    'sticky': False if overall_status == 'success' else True,
                    'next': {
                        'type': 'ir.actions.act_window',
                        'res_model': 'db.backup.log',
                        'res_id': log_rec.id,
                        'view_mode': 'form',
                        'target': 'current',
                    }
                }
            }
        return True
