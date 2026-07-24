# Changelog — sale_lot_report

Historial generado automáticamente a partir de `git log -- sale_lot_report`. No es prosa editorial: cada línea es un commit real. Mantener actualizado: después de modificar este módulo, anteponer la entrada nueva bajo la fecha de hoy (o crear el día si no existe).

**Commits registrados:** 86 | **Rango:** 2026-04-15 → 2026-06-10

---


## 2026-06-10

- 📚 `678aa01` docs(global): auditoria de modulos, actualizacion de documentacion, propuesta de engine v2 y estructura inicial de manuales visuales para usuarios

## 2026-05-19

- 🔧 `094a34a` chore(core): normalizar formato eof en modulos puente legacy
- 🐛 `1757093` fix(core): restaurar modulos puente legacy para resolver estados inconsistentes y loop de actualizacion en test
- 🔄 `af30ff8` refactor(repo): fusionar módulos de lotes y reportes — lot_selection + pharma_reports

## 2026-05-15

- 🐛 `6905f5f` fix(sale): auditoria preventiva del flujo de cotizaciones — 5 correcciones criticas

## 2026-05-13

- 🐛 `4c1b378` fix(reports): erradicacion de cfdi nativo duplicado, correccion de paginacion en facturas y estandarizacion de layout en ventas e inventario
- 🐛 `1755344` fix(reports): reposiciona cfdi fuera del overflow-hidden, depura tabla cfdi y aplica paleta brand unificada a totales en factura/cotizacion/oc
- 🐛 `e6cbb78` fix(reports): correccion de anchos fijos en tabla cfdi, unificacion tipografica de totales y estandarizacion de layout en todos los reportes
- 🐛 `2d0d8d5` fix(reports): unificacion visual factura/cotizacion - cfdi desbloqueado, totales limpios, descuento duplicado removido

## 2026-05-11

- 🐛 `1e84080` fix(custom_invoice_format): clean invoice line bindings and uppercase thead
- ✨ `1b2390e` feat(reports): standardize pharma layout across invoice/sale/purchase/delivery

## 2026-05-04

- 🐛 `e9e115e` fix(purchase_invoice_parser): restore PDF lot review flow

## 2026-04-30

- 🐛 `afcad64` fix(purchase_order_report): suppress native layout header for OC
- 🐛 `619f7c6` fix(purchase_order_report): render pharma header/address and remove duplicate totals
- ✨ `ca65aaf` feat(purchase_order_report): replicate sale quotation pharma layout
- ✨ `133a65a` feat(sale_lot_report): integrar custom_invoice_format como dependencia

## 2026-04-27

- 🐛 `ea2e0c2` fix(sale_lot_report): eliminar columnas Lote/Caducidad duplicadas en delivery
- 🐛 `cfc6196` fix(sale_lot_report): suprimir bloque nativo de direccion en sale y delivery
- ✨ `daf835c` feat(sale_lot_report): ocultar columna Cliente en delivery slip
- 🐛 `13ba75d` fix(sale_lot_report): no romper cadena t-if/t-elif entre stock_move_table y stock_move_line_table
- 🐛 `5e1cb37` fix(sale_lot_report): eliminar inherits sobre fragmentos serial/aggregated
- 🐛 `a0a25cf` fix(sale_lot_report): xpath //tr falla en templates fragmento de fila
- 🐛 `a515d51` fix(sale_lot_report): resolve t-elif SyntaxError in delivery slip
- 🐛 `257826a` fix: remove templates that break t-elif inheritance in delivery report

## 2026-04-26

- 🐛 `42a88c3` fix: eliminate last remaining t-elif/t-else directives to prevent SyntaxError
- 🔄 `b8e5282` refactor: use independent t-if logic to avoid t-elif syntax errors and inheritance conflicts
- 🐛 `cd6eb2c` fix: resolve ParseError th_discount not found by using t-set logic
- 🐛 `3d5dd0f` fix: resolve SyntaxError t-elif by using position='replace' for hiding elements
- 🐛 `cc0bdd8` fix: resolve KeyError 'company' in pharma_company_address_block
- • `2a8e825` [FIX] sale_lot_report: polish bw report layout
- • `85b98cc` [FIX] sale_lot_report: restore pdf header layout
- 🐛 `63cdd56` fix(sale_lot_report): mover pharma_full_header a body y limpiar duplicados
- 🐛 `d270421` fix(sale_lot_report): xpath flexible para layouts non-standard
- ✨ `ed2d18c` feat(sale_lot_report): restaurar layout completo del mockup
- 🐛 `363bd8a` fix(sale_lot_report): t-field requiere notación record.field con punto
- 🐛 `09dffd7` fix(sale_lot_report): eliminar xpath //h2 que falla en Odoo 19
- • `5a79997` [IMP] sale_lot_report: refactor report layout for odoo 19
- 🐛 `f8ed1ff` fix(sale_lot_report): cerrar gap visual con mockup "Orden de Venta Final"
- 💄 `d253701` style(sale_lot_report): unificar font-size inline a 0.75rem (Handoff §3)
- 🐛 `f4c1f47` fix(sale_lot_report): mover estilos a web.report_assets_common
- 💄 `c351269` style(sale_lot_report): aplicar paleta y tipografía del Handoff Odoo 19
- ✨ `57be0fc` feat(sale_lot_report): añadir meta-band Vendedor|RFC|Contacto al header

## 2026-04-25

- 🐛 `8cd6d07` fix(sale_lot_report): usar hasclass() en lugar de contains(@class) en xpath
- ✨ `2be1235` feat(sale_lot_report): replicar diseño "Orden de Venta Final" en reportes QWeb

## 2026-04-24

- 💄 `bf025aa` style(sale_lot_report): acercar columnas Sucursal|Cliente y separar de logo
- 🐛 `494e15f` fix(sale_lot_report): contener nombre de cliente largo dentro del header
- 📚 `9e47725` docs(sale_lot_report): documentar por qué no se usa formatLang en QWeb
- 🐛 `bd7c8a8` fix(sale_lot_report): reemplazar formatLang por widget float en columna Descuento
- • `844536c` revert+fix(sale_lot_report): restaurar footer y forzar visibilidad de RFC
- ✨ `799921e` feat(sale_lot_report): centrar header y ocultar footer promocional en venta/entrega
- 💄 `2be74f5` style(sale_lot_report): header Sucursal|Cliente compacto y tipografía legible
- 💄 `b2e7917` style(sale_lot_report): unificar columna Impuestos a 0.7rem
- 💄 `46f9285` style(sale_lot_report): unificar tipografia tabla y totales a 0.7rem
- 💄 `4aaf0b6` style(sale_lot_report): arreglar superposicion header y reducir nombre producto a 0.7rem
- 🐛 `9dad608` fix(sale_lot_report): corregir nombre de celda td_name → td_product_name
- 💄 `ad6d470` style(sale_lot_report): header Sucursal|Cliente pegadas y jerarquía tipográfica homogénea
- ✨ `e52af9b` feat(sale_lot_report): replicar header Sucursal|Cliente en sale order y fixes de formato
- 🐛 `bb344c9` fix(sale_lot_report): volver a Bootstrap grid para Sucursal|Cliente
- 💄 `d6f5c87` style(sale_lot_report): divisor vertical entre Sucursal|Cliente y ajuste de padding
- 💄 `93ff33b` style(sale_lot_report): reducir separacion Sucursal|Cliente y subir font-size a 15px
- 💄 `16ac0fe` style(sale_lot_report): usar table-layout fijo para forzar Sucursal|Cliente en paralelo
- 💄 `e980cbc` style(sale_lot_report): juntar columnas Sucursal|Cliente y subir font-size a 13px
- 🐛 `6582579` fix(sale_lot_report): reemplazar hasattr() por acceso directo a o._name (QWeb safe_eval)
- ✨ `fc50cd4` feat(sale_lot_report): aprovechar espacio al lado del logo con columnas Sucursal|Cliente
- 🐛 `37e5935` fix(sale_lot_report): eliminar espacio en blanco entre logo y direcciones

## 2026-04-23

- 🐛 `7d3cd88` fix(sale_lot_report): ocultar company_address en TODOS los layouts de Odoo 19
- 🐛 `23153e0` fix(sale_lot_report): eliminar XPaths redundantes que rompían el parse del layout
- 🐛 `f2d53b0` fix(sale_lot_report): corregir ValueError incomplete format en sale_order_report
- 🐛 `b5c27c8` fix(sale_lot_report): eliminar definitivamente info empresa y RFC duplicado del header
- 🐛 `ad27f59` fix(sale_lot_report): ocultar info empresa en header y reestructurar direcciones
- 🐛 `d851141` fix(sale_lot_report): reducir texto empresa y evitar duplicación cliente/dirección
- 🐛 `ef93672` fix(sale_lot_report): corregir xpath en external_layout_standard para build en Odoo.sh
- ✨ `cfe5e07` feat(sale_lot_report): rediseño estructural de layout y alineación de direcciones
- 🐛 `42453a2` fix(sale_lot_report): eliminar columna Código de Barras para evitar warnings
- 🔧 `7bbc8d8` chore(sale_lot_report): auditoría completa contra infraestructura Odoo 19
- ✨ `d085123` feat(sale_lot_report): ocultar columnas nativas duplicadas en delivery slip
- 🐛 `5d6caee` fix(sale_lot_report): reescritura basada en estructura real de Odoo 19
- 🐛 `4a27a68` fix(sale_lot_report): XPath más tolerantes para insertar celdas en delivery slip
- 🐛 `1e6885a` fix(sale_lot_report): corregir XPath de ocultación para product_expiry
- 🐛 `ee6a228` fix(sale_lot_report): corregir XPath y lógica de ocultación en delivery slip
- 🐛 `206865a` fix(sale_lot_report): ocultar columnas nativas duplicadas en delivery slip
- ✨ `5158208` feat(sale_lot_report): columnas farmacia en reporte de entrega (delivery slip)
- ✨ `bd5a415` feat(sale_lot_report): columnas de farmacia en reporte PDF de venta

## 2026-04-15

- 🔧 `d56d6cc` chore: actualiza autor y website en manifests de módulos personalizados
- 🐛 `1602f2a` fix: sale_lot_report — corrige inherit_id y XPaths para Odoo 19
- ✨ `1af2c0b` feat: sale_lot_report v1 — muestra lote/serie en reporte QWeb de cotización/venta
