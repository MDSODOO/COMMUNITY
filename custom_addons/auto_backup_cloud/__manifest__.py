# -*- coding: utf-8 -*-
{
    'name': 'Cloud & Remote Automated Database Backup',
    'version': '19.0.1.0.0',
    'category': 'Administration/Technical',
    'summary': 'Automated database backups (ZIP with filestore or dump) with Google Drive & SFTP integration from Settings',
    'author': 'Medicine Depot / Quifamesa',
    'website': 'https://github.com/medicinedepot',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'base_setup',
        'mail',
    ],
    'external_dependencies': {
        'python': ['paramiko', 'requests', 'cryptography'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/db_backup_log_views.xml',
        'views/db_backup_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
