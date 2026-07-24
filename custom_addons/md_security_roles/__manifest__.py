{
    'name': 'MDS - Roles de Seguridad Operativos',
    'summary': 'Grupos de seguridad, ACLs y reglas de registro para la migración Enterprise -> Community. / Security groups, ACLs and record rules for the Enterprise -> Community migration.',
    'version': '19.0.1.0.0',
    'category': 'Administration',
    'author': 'MedicineDepot Sureste',
    'license': 'LGPL-3',
    'depends': ['base', 'point_of_sale', 'purchase', 'stock', 'account', 'sales_team'],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
    ],
    'installable': True,
    'application': False,
}
