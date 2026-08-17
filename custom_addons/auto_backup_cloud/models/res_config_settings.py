# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    backup_config_id = fields.Many2one(
        'db.backup.config',
        string='Configuración de Respaldo',
        compute='_compute_backup_config',
        readonly=True,
    )
    backup_db_name = fields.Char(string='Base de Datos Activa', readonly=True)
    backup_format = fields.Selection(
        [
            ('zip', 'ZIP con Filestore (Recomendado)'),
            ('dump', 'Dump SQL Comprimido (pg_dump custom format)'),
        ],
        string='Formato de Respaldo',
        default='zip',
    )
    backup_with_filestore = fields.Boolean(string='Incluir Filestore', default=True)

    # Local
    backup_local_active = fields.Boolean(string='Almacenamiento Local en Servidor', default=True)
    backup_local_dir = fields.Char(string='Ruta Local', default='/var/lib/odoo/backups')
    backup_retention_type = fields.Selection(
        [
            ('days', 'Por Días de Antigüedad'),
            ('count', 'Por Número de Respaldos Recientes'),
        ],
        string='Política de Retención Local',
        default='days',
    )
    backup_retention_days = fields.Integer(string='Días de Retención Local', default=7)
    backup_retention_count = fields.Integer(string='Máximo de Respaldos Locales', default=10)

    # Google Drive
    backup_gdrive_active = fields.Boolean(string='Habilitar Google Drive')
    backup_gdrive_auth_type = fields.Selection(
        [
            ('service_account', 'Service Account (Cuenta de Servicio JSON)'),
            ('oauth', 'OAuth2 (Refresh Token / Client ID / Secret)'),
        ],
        string='Tipo de Autenticación Google',
        default='service_account',
    )
    backup_gdrive_service_account_json = fields.Text(string='JSON de Service Account')
    backup_gdrive_client_id = fields.Char(string='Client ID')
    backup_gdrive_client_secret = fields.Char(string='Client Secret')
    backup_gdrive_refresh_token = fields.Char(string='Refresh Token')
    backup_gdrive_folder_id = fields.Char(string='ID de Carpeta en Drive')
    backup_gdrive_retention_days = fields.Integer(string='Días de Retención en Drive', default=14)

    # SFTP / Remote Server
    backup_sftp_active = fields.Boolean(string='Habilitar Envío SFTP/SSH')
    backup_sftp_host = fields.Char(string='Host SFTP')
    backup_sftp_port = fields.Integer(string='Puerto SFTP', default=22)
    backup_sftp_user = fields.Char(string='Usuario SFTP')
    backup_sftp_auth_type = fields.Selection(
        [
            ('password', 'Contraseña'),
            ('key', 'Clave Privada SSH'),
        ],
        string='Autenticación SFTP',
        default='key',
    )
    backup_sftp_password = fields.Char(string='Contraseña SFTP')
    backup_sftp_private_key = fields.Text(string='Clave Privada SSH')
    backup_sftp_passphrase = fields.Char(string='Frase de Paso Clave SSH')
    backup_sftp_remote_dir = fields.Char(string='Directorio Remoto SFTP', default='/backups/odoo')
    backup_sftp_retention_days = fields.Integer(string='Días de Retención en SFTP', default=14)

    # Cron
    backup_cron_active = fields.Boolean(string='Programación Automática (Cron)')
    backup_cron_interval_number = fields.Integer(string='Intervalo', default=1)
    backup_cron_interval_type = fields.Selection(
        [
            ('hours', 'Horas'),
            ('days', 'Días'),
            ('weeks', 'Semanas'),
        ],
        string='Unidad',
        default='days',
    )

    # Estado
    backup_last_date = fields.Datetime(string='Último Respaldo', readonly=True)
    backup_last_status = fields.Selection(
        [
            ('success', 'Exitoso'),
            ('warning', 'Parcial / Con Advertencias'),
            ('error', 'Fallido'),
        ],
        string='Estado del Último Respaldo',
        readonly=True,
    )

    def _get_primary_backup_config(self):
        Config = self.env['db.backup.config'].sudo()
        cfg = Config.search([('active', '=', True)], limit=1)
        if not cfg:
            cfg = Config.search([], limit=1)
        if not cfg:
            cfg = Config.create({
                'name': 'Configuración Principal de Respaldo',
                'backup_format': 'zip',
                'with_filestore': True,
                'local_backup_active': True,
                'local_backup_dir': '/var/lib/odoo/backups',
            })
        return cfg

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        cfg = self._get_primary_backup_config()
        res.update(
            backup_config_id=cfg.id,
            backup_db_name=self.env.cr.dbname,
            backup_format=cfg.backup_format or 'zip',
            backup_with_filestore=cfg.with_filestore,
            backup_local_active=cfg.local_backup_active,
            backup_local_dir=cfg.local_backup_dir or '/var/lib/odoo/backups',
            backup_retention_type=cfg.retention_type or 'days',
            backup_retention_days=cfg.retention_days or 7,
            backup_retention_count=cfg.retention_count or 10,
            backup_gdrive_active=cfg.gdrive_active,
            backup_gdrive_auth_type=cfg.gdrive_auth_type or 'service_account',
            backup_gdrive_service_account_json=cfg.gdrive_service_account_json or '',
            backup_gdrive_client_id=cfg.gdrive_client_id or '',
            backup_gdrive_client_secret=cfg.gdrive_client_secret or '',
            backup_gdrive_refresh_token=cfg.gdrive_refresh_token or '',
            backup_gdrive_folder_id=cfg.gdrive_folder_id or '',
            backup_gdrive_retention_days=cfg.gdrive_retention_days or 14,
            backup_sftp_active=cfg.sftp_active,
            backup_sftp_host=cfg.sftp_host or '',
            backup_sftp_port=cfg.sftp_port or 22,
            backup_sftp_user=cfg.sftp_user or '',
            backup_sftp_auth_type=cfg.sftp_auth_type or 'key',
            backup_sftp_password=cfg.sftp_password or '',
            backup_sftp_private_key=cfg.sftp_private_key or '',
            backup_sftp_passphrase=cfg.sftp_passphrase or '',
            backup_sftp_remote_dir=cfg.sftp_remote_dir or '/backups/odoo',
            backup_sftp_retention_days=cfg.sftp_retention_days or 14,
            backup_cron_active=cfg.cron_active,
            backup_cron_interval_number=cfg.cron_interval_number or 1,
            backup_cron_interval_type=cfg.cron_interval_type or 'days',
            backup_last_date=cfg.last_backup_date,
            backup_last_status=cfg.last_backup_status,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        cfg = self._get_primary_backup_config()
        cfg.write({
            'backup_format': self.backup_format,
            'with_filestore': self.backup_with_filestore,
            'local_backup_active': self.backup_local_active,
            'local_backup_dir': self.backup_local_dir,
            'retention_type': self.backup_retention_type,
            'retention_days': self.backup_retention_days,
            'retention_count': self.backup_retention_count,
            'gdrive_active': self.backup_gdrive_active,
            'gdrive_auth_type': self.backup_gdrive_auth_type,
            'gdrive_service_account_json': self.backup_gdrive_service_account_json,
            'gdrive_client_id': self.backup_gdrive_client_id,
            'gdrive_client_secret': self.backup_gdrive_client_secret,
            'gdrive_refresh_token': self.backup_gdrive_refresh_token,
            'gdrive_folder_id': self.backup_gdrive_folder_id,
            'gdrive_retention_days': self.backup_gdrive_retention_days,
            'sftp_active': self.backup_sftp_active,
            'sftp_host': self.backup_sftp_host,
            'sftp_port': self.backup_sftp_port,
            'sftp_user': self.backup_sftp_user,
            'sftp_auth_type': self.backup_sftp_auth_type,
            'sftp_password': self.backup_sftp_password,
            'sftp_private_key': self.backup_sftp_private_key,
            'sftp_passphrase': self.backup_sftp_passphrase,
            'sftp_remote_dir': self.backup_sftp_remote_dir,
            'sftp_retention_days': self.backup_sftp_retention_days,
            'cron_active': self.backup_cron_active,
            'cron_interval_number': self.backup_cron_interval_number,
            'cron_interval_type': self.backup_cron_interval_type,
        })

    def _compute_backup_config(self):
        for record in self:
            record.backup_config_id = record._get_primary_backup_config().id

    def action_backup_cloud_now(self):
        self.execute()
        cfg = self._get_primary_backup_config()
        return cfg.action_backup_now()

    def action_backup_cloud_test_gdrive(self):
        self.execute()
        cfg = self._get_primary_backup_config()
        return cfg.action_test_gdrive()

    def action_backup_cloud_test_sftp(self):
        self.execute()
        cfg = self._get_primary_backup_config()
        return cfg.action_test_sftp()

    def action_backup_cloud_open_logs(self):
        return self.env['ir.actions.act_window']._for_xml_id('auto_backup_cloud.action_db_backup_log')

    def action_backup_cloud_open_config(self):
        cfg = self._get_primary_backup_config()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Configuración Avanzada de Respaldo'),
            'res_model': 'db.backup.config',
            'res_id': cfg.id,
            'view_mode': 'form',
            'target': 'current',
        }
