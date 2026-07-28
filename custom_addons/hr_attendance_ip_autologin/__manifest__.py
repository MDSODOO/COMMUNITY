{
    'name': 'MDS - Check-in automático por IP de sucursal',
    'summary': (
        'Registra el check-in de asistencia automáticamente cuando un '
        'empleado inicia sesión desde una IP autorizada de su sucursal.'
    ),
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'author': 'MedicineDepot Sureste',
    'license': 'LGPL-3',
    # 1 res.company = 1 sucursal en esta instancia (Cancún, Campeche,
    # Chetumal, Mérida, Playa del Carmen, Ticul) -- ver ATTENDANCE_BASELINE.md.
    'depends': ['hr_attendance', 'web', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_attendance_authorized_ip_views.xml',
        'views/res_company_views.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
}
