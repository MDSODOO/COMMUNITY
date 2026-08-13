# -*- coding: utf-8 -*-
{
    'name': 'Reporte: Trazabilidad Descuento 2% + Cashback 5%',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Reporting',
    'author': 'Medicine Depot, Daniel Cervera',
    'license': 'OPL-1',
    'summary': 'Trazabilidad por cliente/sucursal/mes del esquema de descuento dividido (2% en factura + 5% cashback)',
    'description': """
Reporte de trazabilidad para clientes con esquema de descuento global del 7%,
dividido en:
  - 2%: aplicado directamente como descuento por línea en cada factura.
  - 5%: acumulado como provisión de devolución en efectivo (cashback) a fin de mes.

Agrupado por Cliente, Sucursal (compañía) y Mes. Columnas: Monto Base,
Descuento Aplicado (2%), Total Facturado y Provisión de Cashback (5%).

Alcance: PROSPECTIVO. El reporte solo toma facturas posteadas donde ya se
capturó el descuento por línea (discount > 0) para clientes marcados con el
campo 'Esquema descuento 2% + cashback 5%' en su ficha (res.partner). El
histórico previo a la implementación de este esquema no se reprocesa.

Requiere marcar manualmente a cada cliente elegible en su ficha de contacto.
    """,
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/client_cashback_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
