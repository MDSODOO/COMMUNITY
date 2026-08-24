{
    "name": "POS Payment Rectifier",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Rectifica el método de pago de una orden PoS cerrada (ej. Tarjeta capturada por error en vez de Efectivo) sin desarmar la conciliación de la sesión",
    "description": """
        Cuando un cajero selecciona por error "Tarjeta de Débito/Crédito" en
        vez de "Efectivo" (o viceversa) en una orden de Punto de Venta ya
        cerrada, esta orden queda mezclada dentro de un account.payment
        agregado por sesión+método que no se puede editar de forma segura
        orden por orden.

        Este módulo NO reabre ni desarma esa agregación. En su lugar:
          1. Deja el historial original de pos.payment intacto (nunca se
             reescribe lo que realmente ocurrió en caja).
          2. Publica un asiento contable de reclasificación que mueve el
             monto entre la cuenta puente del método erróneo
             (outstanding_account_id) y la cuenta real del método correcto
             (journal.default_account_id de Efectivo).
          3. Deja un registro permanente de auditoría
             (pos.payment.rectification.log) con motivo, usuario y el
             asiento generado.

        Si la cuenta puente del método erróneo ya fue conciliada contra un
        estado de cuenta bancario real, el wizard bloquea la operación
        automática y la marca como "requiere revisión manual de un contador".
    """,
    "author": "Medicine Depot - Daniel Cervera",
    "depends": ["point_of_sale", "account"],
    "data": [
        "security/pos_payment_rectifier_security.xml",
        "security/ir.model.access.csv",
        "views/pos_payment_rectification_log_views.xml",
        "views/pos_payment_rectifier_wizard_views.xml",
        "views/pos_order_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
