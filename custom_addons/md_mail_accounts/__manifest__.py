{
    'name': 'MDS — Cuentas de Correo (IMAP/SMTP por Usuario)',
    'version': '19.0.1.0.0',
    'category': 'Discuss',
    'summary': 'Configuración IMAP/SMTP individual por usuario con fetching automático',
    'description': """
Permite a cada usuario conectar su cuenta de correo corporativa
(IMAP + SMTP) directamente desde Odoo.

- Almacena credenciales IMAP/SMTP por usuario (cifradas en BD).
- Cron automático cada 5 minutos: conecta IMAP, descarga correos
  nuevos y los crea como mail.mail (state='received') vinculados
  al partner del usuario.
- Los correos aparecen en "Recibidos" del cliente de correo.
- Soporta servidores cPanel/IMAP SSL (mail.medicinedepotsureste.mx).
    """,
    'author': 'MedicineDepot Sureste',
    'depends': ['mail', 'md_mail_client'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/mail_account_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
