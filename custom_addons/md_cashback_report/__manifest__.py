# -*- coding: utf-8 -*-
{
    'name': 'Reporte: Trazabilidad Descuento 2% + Cashback 5%',
    'version': '19.0.5.0.0',
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

v3: Exclusión de productos por cliente — nuevo campo
res.partner.x_cashback_excluded_product_ids. Las líneas de productos no
elegibles se apartan del Monto Base, Descuento Aplicado, Provisión y
Cashback Real, y no cuentan como anomalía. El reporte principal ahora
desglosa Total Facturado (bruto) / Monto Base Excluido / Base Neta
Computable para trazabilidad completa.

v4: Aplicación automática del 2% — account.move.line ahora calcula solo el
% de descuento (0% o 2%) al crear/editar líneas de producto en factura de
clientes con el esquema activo, según su lista de exclusión. Corre a nivel
de ORM (create/write), así que aplica sin importar si la línea viene de la
UI, de una importación o de la API externa que usa el flujo n8n/RPA. Solo
toca líneas de facturas en borrador — nunca reescribe una línea ya posteada.

Alcance: PROSPECTIVO. Solo facturas posteadas para clientes marcados con el
campo 'Esquema descuento 2% + cashback 5%' en su ficha (res.partner).

v5: Refactor UI de la ficha de Contacto. El campo 'Esquema descuento 2% +
cashback 5%' se movió a la pestaña Ventas y Compras (grupo 'Configuración
de Cashback'). Los productos excluidos ya no se muestran como tags en el
formulario principal (rompían el layout con muchos productos); ahora se
gestionan desde un Smart Button ('Productos Excluidos', ícono fa-ban) con
contador dinámico que abre una lista editable en una ventana emergente,
con soporte nativo para agregar/quitar productos.
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
