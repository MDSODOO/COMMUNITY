# -*- coding: utf-8 -*-
##############################################################################
#
#    Device Management Module for Odoo
#    Copyright (C) 2026 Medicine Depot
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

{
    'name': 'Medicine Depot - Activos IT',
    'summary': 'Gestión especializada de dispositivos físicos con control de inventario A la mano',
    'description': '''
        Módulo para gestión integral de dispositivos físicos de Medicine Depot
        (laptops, desktops, monitores, servidores, etc.), con soporte multi-sucursal.

        Características:
        - Control de cantidad A la mano (inventario físico)
        - Historial de asignaciones a usuarios
        - Mantenimiento preventivo y correctivo
        - Gestión de documentación (manuales, garantías, actas)
        - Seguimiento de costos y pagos
        - Suscripciones y licencias de software
        - Calendario de actividades y mantenimientos
        - Auditoría completa con mail.thread
    ''',
    'version': '19.0.1.5.0',
    'category': 'Tools/Asset Management',
    'license': 'LGPL-3',
    'author': 'Medicine Depot, Odoo Community Association (OCA)',
    'website': 'https://github.com/medicine-depot',
    'contributors': [
        'Daniel Cervera <daniel.cervera.2029@gmail.com>',
    ],
    'depends': [
        'base',
        'mail',
        'account',
        'hr',
        'calendar',
        'contacts',
    ],
    'data': [
        # Security
        'security/device_management_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',

        # Views
        'views/device_assignment_views.xml',
        'views/device_maintenance_views.xml',
        'views/device_documentation_views.xml',
        'views/device_payment_views.xml',
        'views/device_subscription_views.xml',
        'views/device_todo_views.xml',
        'views/device_management_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'md_asset_devices/static/src/css/device_management.css',
        ],
    },
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
