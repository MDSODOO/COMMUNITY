{
    "name": "POS Order Transfer",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Ceder/transferir pedidos en borrador entre empleados del POS",
    "description": """
        Permite a los empleados del Punto de Venta transferir (ceder) un pedido
        en curso a otro empleado dentro de la misma sesión de caja.

        Requiere que la función "Inicio de sesión con empleados" esté habilitada
        en la configuración del POS (módulo pos_hr).
    """,
    "author": "Custom Development",
    "depends": ["pos_hr"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_order_transfer/static/src/xml/order_transfer_popup.xml",
            "pos_order_transfer/static/src/xml/actionpad.xml",
            "pos_order_transfer/static/src/js/order_transfer_popup.js",
            "pos_order_transfer/static/src/js/actionpad_patch.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
