{
    'name': 'MDS Helpdesk — Tickets integrados en Proyectos',
    'version': '19.0.1.0.0',
    'category': 'Services/Helpdesk',
    'summary': 'Sistema de tickets de soporte embebido dentro del módulo de Proyectos existente, sin crear proyectos duplicados.',
    'author': 'Medicine Depot Sureste / Daniel Cervera',
    'website': 'https://github.com/MDSODOO/COMMUNITY',
    'depends': ['project', 'mail'],
    'data': [
        'security/mds_helpdesk_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/mds_helpdesk_ticket_views.xml',
        'views/project_project_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
