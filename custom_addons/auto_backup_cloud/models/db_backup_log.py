# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DbBackupLog(models.Model):
    _name = 'db.backup.log'
    _description = 'Registro de Auditoría de Respaldo'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Archivo de Respaldo', required=True, readonly=True)
    config_id = fields.Many2one(
        'db.backup.config',
        string='Configuración',
        ondelete='set null',
        readonly=True,
    )
    db_name = fields.Char(string='Base de Datos', readonly=True)
    backup_format = fields.Selection(
        [
            ('zip', 'ZIP con Filestore'),
            ('dump', 'Dump SQL Comprimido'),
        ],
        string='Formato',
        readonly=True,
    )
    backup_type = fields.Selection(
        [
            ('manual', 'Manual'),
            ('cron', 'Automático (Cron)'),
        ],
        string='Tipo de Ejecución',
        default='manual',
        readonly=True,
    )
    start_time = fields.Datetime(string='Inicio', readonly=True)
    end_time = fields.Datetime(string='Fin', readonly=True)
    duration_seconds = fields.Float(string='Duración (s)', digits=(10, 2), readonly=True)
    file_size_bytes = fields.Integer(string='Tamaño (Bytes)', readonly=True)
    file_size_human = fields.Char(string='Tamaño', compute='_compute_file_size_human', store=True)

    # Estados de Destinos
    local_status = fields.Selection(
        [
            ('success', 'Éxito'),
            ('error', 'Fallo'),
            ('skipped', 'Omitido'),
        ],
        string='Almacenamiento Local',
        default='skipped',
        readonly=True,
    )
    local_path = fields.Char(string='Ruta Local', readonly=True)

    gdrive_status = fields.Selection(
        [
            ('success', 'Éxito'),
            ('error', 'Fallo'),
            ('skipped', 'Omitido'),
        ],
        string='Google Drive',
        default='skipped',
        readonly=True,
    )
    gdrive_file_id = fields.Char(string='ID Archivo en Drive', readonly=True)

    sftp_status = fields.Selection(
        [
            ('success', 'Éxito'),
            ('error', 'Fallo'),
            ('skipped', 'Omitido'),
        ],
        string='Servidor Remoto (SFTP)',
        default='skipped',
        readonly=True,
    )
    sftp_remote_path = fields.Char(string='Ruta Remota SFTP', readonly=True)

    overall_status = fields.Selection(
        [
            ('success', 'Exitoso'),
            ('warning', 'Parcial / Con Advertencias'),
            ('error', 'Fallido'),
        ],
        string='Estado General',
        default='success',
        readonly=True,
    )

    details = fields.Text(string='Detalle de Ejecución / Errores', readonly=True)
    purged_files_summary = fields.Text(string='Depuración de Respaldos Anteriores', readonly=True)

    @api.depends('file_size_bytes')
    def _compute_file_size_human(self):
        for record in self:
            size = record.file_size_bytes or 0
            if size <= 0:
                record.file_size_human = '0 B'
                continue
            units = ['B', 'KB', 'MB', 'GB', 'TB']
            idx = 0
            val = float(size)
            while val >= 1024.0 and idx < len(units) - 1:
                val /= 1024.0
                idx += 1
            record.file_size_human = f"{val:.2f} {units[idx]}"
