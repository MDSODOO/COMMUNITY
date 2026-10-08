{
    'name': 'MDS - Check-in biométrico (huella) con geocerca de respaldo',
    'summary': (
        'Exige verificación de huella (WebAuthn/FIDO2) para el check-in '
        'manual de asistencia, validando la ubicación por IP de sucursal '
        '(prioritaria) o por geocerca GPS (respaldo para personal de campo).'
    ),
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'author': 'MedicineDepot Sureste',
    'license': 'LGPL-3',
    # Depende del módulo de IP ya auditado -- reutiliza
    # attendance_authorized_ip_ids / _matches() en vez de duplicar esa
    # lógica. No se modifica ningún archivo de hr_attendance_ip_autologin.
    'depends': ['hr_attendance_ip_autologin', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_attendance_biometric_security.xml',
        'views/hr_attendance_geofence_views.xml',
        'views/hr_employee_biometric_credential_views.xml',
        'views/hr_attendance_views.xml',
        'views/hr_attendance_biometric_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_attendance_biometric_geofence/static/src/js/biometric_attendance.js',
            'hr_attendance_biometric_geofence/static/src/js/biometric_attendance.xml',
        ],
    },
    'installable': True,
    'application': False,
}
