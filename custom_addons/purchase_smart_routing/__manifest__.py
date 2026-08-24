{
    'name': 'Smart Purchase Routing',
    'version': '19.0.3.0.4',
    'category': 'Inventory/Purchase',
    'summary': 'Enrutamiento inteligente de compras: N proveedores, umbral de precio, fuzzy matching y fallback por stock',
    'description': """
Smart Purchase Routing
======================
Motor de decisión de compras que asigna cada producto al proveedor óptimo
considerando precio efectivo (con soporte de ofertas temporales), stock a la mano
y un umbral de precio configurable para evitar cambios de proveedor innecesarios.

Funcionalidades:
- Comparador de 2 catálogos Excel (Proveedor A preferido vs Proveedor B alternativo)
  con búsqueda difusa (fuzzy) por nombre/descripción y regla del 6% configurable
- Auto-asignación de default_code desde el catálogo del proveedor si el producto no tiene SKU
- Registro de excepciones: artículos no encontrados reportados en chatter y resumen HTML
- Importación de catálogos de proveedores (Excel) con precios, stock y ofertas
- Umbral de precio configurable (default 6%): solo cambia de proveedor si la diferencia supera el umbral
- Motor de N proveedores con fallback automático por stock
- Importación de demanda desde Órdenes de Compra existentes o desde Excel
- Sesión de routing persistente con trazabilidad completa por decisión
- Generación de POs en estado borrador o confirmado (configurable)
- Integración con Configuración → Compras para parámetros globales
    """,
    'author': 'QUIFAMESA',
    'license': 'LGPL-3',
    'depends': [
        'purchase',
        'stock',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        # Las vistas de wizards primero — definen los actions que referencian las vistas de modelos
        'wizards/supplier_catalog_import_views.xml',
        'views/routing_demand_import_views.xml',
        'views/routing_catalog_compare_views.xml',
        # Vistas de modelos después — ya pueden referenciar los actions de los wizards
        'views/product_supplierinfo_views.xml',
        'views/purchase_routing_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
