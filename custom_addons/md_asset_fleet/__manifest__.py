# -*- coding: utf-8 -*-
{
    'name': 'Medicine Depot - Activos Vehiculares',
    'summary': 'Vinculación de la flotilla vehicular a empleados y sucursales de Medicine Depot',
    'description': '''
        Extiende el módulo Fleet nativo de Odoo para operar la flotilla de
        Medicine Depot (vehículos de reparto/servicio) vinculada a empleados
        (hr.employee) y a la sucursal (company_id, ya nativo en fleet.vehicle).

        No duplica el módulo Fleet: solo agrega el vínculo a hr.employee y lo
        expone en la vista de formulario existente.
    ''',
    'version': '19.0.1.0.0',
    'category': 'Tools/Asset Management',
    'license': 'LGPL-3',
    'author': 'Medicine Depot',
    'website': 'https://github.com/medicine-depot',
    'contributors': [
        'Daniel Cervera <daniel.cervera.2029@gmail.com>',
    ],
    'depends': [
        'fleet',
        'hr',
    ],
    'data': [
        'views/fleet_vehicle_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
