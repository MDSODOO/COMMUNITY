# Changelog — pharma_reports

Historial generado automáticamente a partir de `git log -- pharma_reports`. No es prosa editorial: cada línea es un commit real. Mantener actualizado: después de modificar este módulo, anteponer la entrada nueva bajo la fecha de hoy (o crear el día si no existe).

**Commits registrados:** 65 | **Rango:** 2026-05-19 → 2026-06-29

---


## 2026-07-02

- 🐛 fix(pharma_reports): remover bloque de trazabilidad "Factura(s) de Proveedor / Nota(s) de Compra" del reporte de Orden de Compra — se relocaliza (con campos distintos) al reporte de Reembolso a proveedor en custom_invoice_format

## 2026-07-01

- 🎨 fix(pharma_reports): reubicar trazabilidad de OC entre la meta-band (Comprador/RFC/Contacto) y el bloque Sucursal/Proveedor, con formato meta-band (grey box)
- ✨ feat(pharma_reports): trazabilidad cruzada (facturas/notas de compra) en reporte de OC y devoluciones; ocultar complemento CFDI en devoluciones a proveedor

## 2026-06-30

- 🐛 fix(pharma_reports): agregar stock.scrap.batch a guards de layout — suprime header nativo en consolidado de bajas

## 2026-06-29

- ✨ `77fe3c8` feat(custom_invoice_format): rediseño complemento CFDI 4.0 con guía visual [19.0.1.18.0]
- 🐛 `9d2f71c` fix(pharma_reports): improve cfdi invoice footer layout
- 🔄 `2d3e482` refactor(reports): aislar lotes en sub-template y unificar guards XPath h2|h3

## 2026-06-22

- 🐛 `56d43ef` fix(pharma_reports): actualizar external id obsoleto de la vista de inventario para compatibilidad con odoo 19 manteniendo la traduccion a la mano

## 2026-06-18

- 🐛 `b95f2c3` fix(pharma_reports): recuperar concentrado de variaciones con 3 tarjetas (lineas, variacion piezas/costo)
- 🐛 `3c6681b` fix(pharma_reports): simplificar reporte fisico y agregar exportacion excel
- 🐛 `86182f6` fix(pharma_reports): ajustar concentrado y columnas de variacion fisica
- 🐛 `a2e50a9` fix(pharma_reports): centrar concentrado y unificar tabla fisica
- 🐛 `b5fdab5` fix(pharma_reports): compactar concentrado y columnas del reporte fisico
- 🐛 `6973f80` fix(pharma_reports): ajustar columnas y margen superior del reporte fisico
- 🐛 `70d70df` fix(pharma_reports): remover header nativo y ajustar sizing de reporte fisico
- 🐛 `5dc1a98` fix(pharma_reports): corregir linea producto y variaciones en inventario fisico
- ✨ `090d1df` feat(pharma_reports): complementar reporte de inventario fisico con costos
- 🐛 `48fb6a2` fix(pharma_reports): reemplazar context_today obsoleto por datetime.date.today en QWeb para evitar KeyError al generar reporte PDF
- 🐛 `6cb3e0d` fix(pharma_reports): actualizar external ID de herencia de stock.quant para compatibilidad con Odoo 19
- 🔧 `6b3ad60` chore(pharma_reports): agregar pruebas unitarias para reporte de inventario fisico y actualizar README
- ✨ `b352935` feat(pharma_report): auditar inventario fisico con playwright, mejorar UI de ajustes y crear reporte PDF estilizado
- 🐛 `60469c3` fix(pharma_reports): restaurar diseño inline de lotes y añadir cantidad por lote en transferencias
- ✨ `b3716f6` feat(pharma_reports): desglosar productos por lote en lineas independientes en el reporte PDF de transferencias internas

## 2026-06-16

- 🐛 `8167061` fix(purchase_invoice_parser): remover encabezado duplicado en reporte PDF y colapsar margen superior vacio

## 2026-06-11

- 🐛 `c342577` fix(pharma_reports): eliminar espacio en blanco inicial en reporte PDF de recepción de mercancía

## 2026-06-10

- 🔧 `87c9bfe` chore(global): cobertura de tests para 6 modulos, estructura pharma_reports y bump de versiones
- 📚 `678aa01` docs(global): auditoria de modulos, actualizacion de documentacion, propuesta de engine v2 y estructura inicial de manuales visuales para usuarios

## 2026-06-08

- 🐛 `d44a692` fix(pharma_reports/migrations): actualizacion de metodo de limpieza de cache obsoleto en script de post-migracion para compatibilidad con odoo 19
- 🐛 `aadc526` fix(stock/reports): erradicacion global de variable obsoleta has_packages en todas las vistas residuales de studio para prevenir colapsos en pdf

## 2026-06-06

- 🐛 `43b63d1` fix(reports): restauracion de maquetacion qweb desde main para solucionar solapamiento en pdfs de compras y operaciones
- 🐛 `0a4146a` fix(pharma_reports): actualizacion de selectores xpath en layout overrides para asegurar compatibilidad con la estructura del header en odoo 19
- 🐛 `44d5c42` fix(reports): suprimir div.header nativo del layout en compras y picking para eliminar solapamiento de direcciones
- 🐛 `535ef1c` fix(reports): refactorizacion de maquetacion qweb usando bootstrap 5 para resolver solapamiento de direcciones y tablas en pdfs de compras e inventario
- 🐛 `0b9c615` fix(pharma_reports): actualizacion de campo iterador a move_ids en reporte transferencias para compatibilidad con odoo 19
- ✨ `03afa5d` feat(stock/reports): creacion de reporte qweb nativo transferencias con integracion de carta porte y estructura de bajas
- 🐛 `42098ce` fix(stock/reports): eliminacion de variable obsoleta has_packages en plantilla de albaran para restaurar impresion de pdf

## 2026-05-28

- 🐛 `e5a380d` fix(inventory): recibo de entrega con columnas Pedido (A la mano) y Entregado, y arreglo del divisor de header que dejaba hueco blanco
- 🐛 `0ec8bf4` fix(inventory): corregir columnas del recibo de entrega apuntando th por @name y alinear lote/caducidad/cantidad con encabezados

## 2026-05-25

- ✨ `692a059` feat(pharma_reports): isolated sale.order header to stop cross-report regressions
- 🐛 `3aaf8a1` fix(pharma_reports): restore doc-info block on purchase order header

## 2026-05-24

- 🐛 `9596e90` fix(pharma_reports): derive _company from _rec to avoid KeyError
- 🐛 `7b0274d` fix(pharma_reports): inject pharma header in body, not external_layout
- 🐛 `aadfa6a` fix(pharma_reports): clear purchase meta band flow
- 🐛 `d97246c` fix(pharma_reports): align purchase rfq layout
- 🐛 `ed9ef14` fix(pharma_reports): add top space to purchase paperformat
- 🐛 `f514085` fix(pharma_reports): stabilize purchase header width
- 🐛 `4e51801` fix(pharma_reports): align purchase order header info
- 🐛 `4f86b42` fix(custom_invoice_format): align invoice report actions
- 🐛 `bf1aad4` fix(pharma_reports): align invoice and purchase headers
- 🐛 `add6268` fix(pharma_reports): align invoice and purchase headers
- 🐛 `22522c1` fix(pharma_reports): cover wave and bubble layouts
- 🐛 `7c910b3` fix(pharma_reports): remove invalid external layout refs
- 🐛 `18dfddb` fix(pharma_reports): hide native purchase header layouts
- 🐛 `57149c8` fix(pharma_reports): correct purchase order address xpath
- 🐛 `1a6d54c` fix(pharma_reports): suppress native PO header elements correctly
- 🐛 `cd1aa6d` fix(pharma_reports): remove non-existent th name xpaths from OC report
- 🐛 `a995bef` fix(pharma_reports): audit and fix purchase order report layout
- ✨ `2a4b614` feat(pharma_reports): replicate invoice layout — inline lot/expiry in description cell
- 🐛 `610bcf3` fix(pharma_reports): show discount column in purchase order report
- 🐛 `73958a2` fix(pharma_reports): remove failing t-call xpath from purchase report overrides

## 2026-05-23

- 🐛 `6e75186` fix(reports): add signature block to scrap batch report

## 2026-05-21

- 🐛 `083f1a4` fix(reports): tratar proforma como cotizacion y ocultar lote caducidad descuento en impresion de cotizaciones
- • `3ef113e` Revert "fix(reports): ocultar lote caducidad y descuento en cotizaciones manteniendolos en orden de venta"
- 🐛 `e3f4b48` fix(reports): ocultar lote caducidad y descuento en cotizaciones manteniendolos en orden de venta
- 🐛 `a765ea1` fix(reports): alinear colores tipografia y tamano de tablas pharma al golden template sin cambios estructurales
- 🐛 `a05f653` fix(reports): aislar estandarizacion visual a factura cliente y restaurar diseno establecido de compras
- 🐛 `8c5bdfd` fix(reports): correccion de sintaxis xpath eliminando node() en replace para evitar TypeError de lxml en report_delivery_document
- ✨ `8bdaa7f` feat(reports): abstraccion de diseno de factura a layout global y estandarizacion de qweb para ventas, compras y logistica

## 2026-05-19

- 🔄 `af30ff8` refactor(repo): fusionar módulos de lotes y reportes — lot_selection + pharma_reports
