# -*- coding: utf-8 -*-
{
    'name': 'Reporte: Trazabilidad Descuento 2% + Cashback 5%',
    'version': '19.0.2.0.0',
    'category': 'Accounting/Reporting',
    'author': 'Medicine Depot, Daniel Cervera',
    'license': 'OPL-1',
    'summary': 'Trazabilidad 2%+5% por cliente/sucursal/mes + detección de anomalías de descuento',
    'description': """
Reporte de trazabilidad para clientes con esquema de descuento global del 7%,
dividido en:
  - 2%: aplicado directamente como descuento por línea en cada factura.
  - 5%: acumulado como provisión de devolución en efectivo (cashback) a fin de mes.

Agrupado por Cliente, Sucursal (compañía) y Mes. Columnas: Monto Base,
Descuento Aplicado (2%), Total Facturado, Provisión Cashback (5%) teórica
y Cashback Real (5% solo sobre líneas con 2% capturado).

v2: Nuevo modelo client.cashback.anomaly — vista SQL que expone las líneas de
producto de clientes del esquema donde el descuento es 0%. Disponible en
Contabilidad ▶ Reportes ▶ Anomalías Cashback. Permite al equipo de finanzas
identificar y corregir facturas antes del cierre de mes, y sirve como fuente
de datos para el flujo n8n de notificación de anomalías.

Alcance: PROSPECTIVO. Solo facturas posteadas para clientes marcados con el
campo 'Esquema descuento 2% + cashback 5%' en su ficha (res.partner).
    """,
    'depends': [
        'account',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/client_cashback_report_views.xml',
        'views/client_cashback_anomaly_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
