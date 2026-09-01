# -*- coding: utf-8 -*-
{
    'name': 'Medicine Depot Mobile API',
    'version': '19.0.1.3.0',
    'summary': 'API REST (token firmado + res.users.apikeys) para la app móvil de Medicine Depot: auth, catálogo, sucursales, carrito/pedidos, perfil, direcciones, historial y push.',
    'description': (
        'Expone /api/mobile/v1/* para la app móvil de Medicine Depot. '
        'Arquitectura de auth inspirada en quifamesa_mobile_api (token corto '
        'de sesión + api key de refresh), pero implementada de forma '
        'independiente con la librería estándar (hmac/hashlib) en vez de '
        'PyJWT, que no está instalado en esta imagen (odoo:19.0 stock).'
    ),
    'category': 'Medicine Depot',
    'author': 'Daniel-Cervera',
    'depends': ['base', 'product', 'stock', 'sale', 'portal'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
