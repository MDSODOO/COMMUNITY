# -*- coding: utf-8 -*-
{
    'name': 'AI Fields',
    'version': '19.0.1.6.0',
    'category': 'Technical',
    'summary': 'Ajustes técnicos para campos personalizados',
    'description': """
Normaliza labels de campos Studio y sanea NULLs en columnas requeridas:

* Renombra `x_studio_branch_office` de "Sucursal" a "Sucursal (Oficina)"
  para resolver el warning de Odoo 19 "Duplicate labels".
* Incluye ai.fields.null.sanitizer: modelo técnico que ejecuta limpieza
  de NULLs en cada arranque (account, website, purchase, product).
""",
    'author': 'Medicine Depot',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/field_labels.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
