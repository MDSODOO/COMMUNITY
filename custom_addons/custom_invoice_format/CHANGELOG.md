# Changelog — custom_invoice_format

Historial generado automáticamente a partir de `git log -- custom_invoice_format`. No es prosa editorial: cada línea es un commit real. Mantener actualizado: después de modificar este módulo, anteponer la entrada nueva bajo la fecha de hoy (o crear el día si no existe).

**Commits registrados:** 120 | **Rango:** 2026-04-20 → 2026-06-30

---


## 2026-07-03

- 🐛 fix(custom_invoice_format): migración `19.0.1.19.0` — purgar PDF cacheado en `account_move.invoice_pdf_report_file` para `in_invoice`/`in_refund` (Factura y Nota de Crédito de **proveedor**). La migración `19.0.1.1.0` solo cubría `out_invoice`/`out_refund` (documentos de cliente); las notas de crédito de proveedor emitidas antes del rediseño del header pharma seguían sirviendo el PDF viejo cacheado sin importar que el template ya estuviera corregido — root cause de la inconsistencia visual reportada entre documentos "viejos" y "nuevos" (no era un problema de rama main vs test, el código ya era idéntico)

## 2026-07-02

- 🐛 fix(custom_invoice_format): reubicar el bloque de trazabilidad Orden de Compra/Factura del Reembolso a proveedor — pasa de estar debajo de los totales a estar arriba del bloque Sucursal/Proveedor, justo después del header pharma
- 🐛 fix(custom_invoice_format): ocultar complemento fiscal CFDI 4.0 (Uso CFDI/Política/Forma de pago + bloque Complemento Fiscal CFDI 4.0) en Factura y Reembolso de proveedor (in_invoice/in_refund) — esos datos pertenecen al CFDI ya timbrado del proveedor y no deben reproducirse en reportes internos
- ✨ feat(custom_invoice_format): agregar trazabilidad Orden de Compra + Factura de origen exclusiva del reporte de Reembolso a proveedor (in_refund), reemplazando el bloque equivalente que vivía en el reporte de Orden de Compra

## 2026-06-30

- 🐛 fix(custom_invoice_format): agregar stock.scrap.batch a los 7 guards pharma_invoice_layout_*_hide — evita que priority 1000 sobreescriba la supresión de pharma_reports (priority 999) y reactiva el header nativo en Bajas Consolidado

## 2026-06-29

- 🐛 `b356286` fix(custom_invoice_format): corregir estructura de complemento cfdi 4.0
- ✨ `77fe3c8` feat(custom_invoice_format): rediseño complemento CFDI 4.0 con guía visual [19.0.1.18.0]
- 🐛 `88ba9f2` fix(custom_invoice_format): corregir bloque CFDI comprimido a mitad derecha de página [19.0.1.17.0]
- 🐛 `b5a2c45` fix(cfdi): corregir datos vacíos en PDF y ZeroDivisionError en timbrado global [19.0.1.16.0]
- 🐛 `c3cc8e0` fix(custom_invoice_format): remove fragile invoice title xpath
- 🐛 `479d7d4` fix(custom_invoice_format): move cfdi footer to page body
- 🐛 `47006e4` fix(custom_invoice_format): correct cfdi footer table layout
- 🐛 `3f9dc7f` fix(custom_invoice_format): corregir complemento CFDI duplicado en todos los reportes de contabilidad [19.0.1.12.0]
- 🐛 `03b25e1` fix(custom_invoice_format): corregir layout CFDI — ancho px en td y suprimir QR nativo
- 🐛 `101e271` fix(custom_invoice_format): suprimir header nativo, lotes en vendor bills y CFDI explícito
- ✨ `cec3cdd` feat(custom_invoice_format): replicar diseño OC en reportes de factura y nota de crédito
- 🔄 `2d3e482` refactor(reports): aislar lotes en sub-template y unificar guards XPath h2|h3

## 2026-06-10

- 🔧 `87c9bfe` chore(global): cobertura de tests para 6 modulos, estructura pharma_reports y bump de versiones
- 📚 `678aa01` docs(global): auditoria de modulos, actualizacion de documentacion, propuesta de engine v2 y estructura inicial de manuales visuales para usuarios
- • `dfd8b37` improvement(theme): comprehensive typography and sizing audit fixes

## 2026-06-06

- 🐛 `61940b7` fix(custom_invoice_format/reports): robustez de xpath para titulo de factura en layouts folder/wave/bubble
- 🐛 `ee244cb` fix(custom_invoice_format/reports): restauracion de selectores xpath especificos en overrides de external_layout para eliminar solapamiento de header en facturas
- 🐛 `b644ad4` fix(reports): corrige superposicion de header nativo en reportes pdf

## 2026-05-25

- 🐛 `351a087` fix(custom_invoice_format): inject pharma header in body and unify SAT cols
- • `2009f4d` Revert "fix(custom_invoice_format): inject SAT columns on vendor bill report"
- 🐛 `6c68709` fix(custom_invoice_format): inject SAT columns on vendor bill report

## 2026-05-24

- 🐛 `ed908eb` fix(custom_invoice_format): import migration via odoo addons
- 🐛 `762b93e` fix(custom_invoice_format): use invoice report action ids
- 🐛 `4f86b42` fix(custom_invoice_format): align invoice report actions
- 🐛 `e2e417e` fix(custom_invoice_format): correct folder title xpath
- 🐛 `bf1aad4` fix(pharma_reports): align invoice and purchase headers
- 🐛 `add6268` fix(pharma_reports): align invoice and purchase headers

## 2026-05-21

- 🐛 `a05f653` fix(reports): aislar estandarizacion visual a factura cliente y restaurar diseno establecido de compras

## 2026-05-19

- 🐛 `af98d17` fix(core): resolucion de modulos inconsistentes y limpieza de dependencias rotas en pharma_reports y manifiestos globales

## 2026-05-15

- • `2e156e3` improvement(custom_invoice_format): mover columna precio unitario para quedar despues de cantidad en reporte pdf
- • `52f5657` improvement(custom_invoice_format): restaurar columna ClaveUnidad y reducir fuente de tabla de lineas para ajuste de 9 columnas
- • `439d839` improvement(custom_invoice_format): reubicacion de la columna precio unitario a la derecha del codigo de producto en el reporte pdf

## 2026-05-14

- • `e28bccc` improvement(custom_invoice_format): tabla totales en mayusculas con font-size unificado
- • `b02ba87` improvement(custom_invoice_format): tabla unica totales con table-layout auto ajustada al contenido
- • `762357c` improvement(custom_invoice_format): tablas datos fiscales y totales en paralelo con clases CSS unificadas
- • `ddfa40e` improvement(custom_invoice_format): unificar datos fiscales e importes en tabla unica con diseno consistente
- • `9dba285` improvement(custom_invoice_format): tablas datos fiscales y totales en paralelo con estilos unificados
- • `fca2972` improvement(custom_invoice_format): unificar diseno de tabla datos fiscales con estilo de tabla totales
- • `43dc48b` improvement(custom_invoice_format): mover tabla datos fiscales encima de totales como seccion independiente
- • `b01b70d` improvement(custom_invoice_format): rediseno de seccion de totales con tabla de datos fiscales y cantidad en letras
- • `83b2b38` improvement(custom_invoice_format): eliminacion de widget de pagos y etiqueta cfdi publico en general del layout de la factura
- 🐛 `76c80e6` fix(invoice): eliminar fix_mx_cfdi_compat.xml — xpath roto en Odoo 19
- 🐛 `7dd3d94` fix(main): hotfix global — not-null constraints SQL + campo l10n_mx_cfdi_to_public deprecado
- ✨ `7d9baf4` feat(invoice): añadir uso del CFDI y CFDI al público general en totales
- 🐛 `95d0b3e` fix(invoice): agregar 'Política de pago' y actualizar 'Forma de pago' con campos CFDI 4.0
- 🐛 `e4bcf39` fix(invoice): cambiar título primera columna a 'CLAVE' y mejorar lógica obtención forma de pago
- 🐛 `9836ca5` fix(invoice): eliminar columna 'Código del producto' (default_code) de tabla líneas
- 🐛 `84058db` fix(invoice): cambiar 'Método de pago' a 'Forma de pago' y traer política de pago desde tabla totales
- 🐛 `3469972` fix(invoice): tabla totales con metodo pago, cantidad pagada escrita y optimizacion font sizes
- 🐛 `354e3c6` fix(invoice): correcciones finales - codigo producto, numero recibo dinamico, alineacion totales y espacios
- ✨ `e09df9e` feat(invoice): reestructuracion de columnas a CLAVE, ajuste de encabezado RFC/Uso CFDI y alineacion de totales
- 🐛 `8e7c2f2` fix(global): auditoría de rama test y aplicación de correcciones críticas nivel 1 (acls, sintaxis y dependencias)
- 🐛 `eacdb6c` fix(invoice): tabla totales full-width real + supresion robusta de columna codigo de la unidad
- 🐛 `0ed6988` fix(invoice): tabla de totales replica exacta del lenguaje de tabla de lineas
- 🐛 `3229c14` fix(invoice): unifica baseline tipografico cliente/proveedor al tamano mas chico
- 🐛 `f3638af` fix(invoice): tabla de totales con mismo lenguaje visual que tabla de lineas
- 🐛 `0ab6788` fix(invoice): elimina columna codigo de la unidad y totales full-width como tabla de lineas
- 🐛 `9b601f3` fix(invoice): rediseno tabla de totales (ancho 42%, borde definido, jerarquia clara)
- 🐛 `650cedf` fix(invoice): retira info de pago del bloque totales y unifica tamanos cliente/proveedor
- 🐛 `17dfa1e` fix(invoice): totales debajo de la tabla de productos, cfdi al final
- 🐛 `cf4a57a` fix(invoice): restaura cfdi nativo y columnas sat conservando totales custom

## 2026-05-13

- 🐛 `4c1b378` fix(reports): erradicacion de cfdi nativo duplicado, correccion de paginacion en facturas y estandarizacion de layout en ventas e inventario
- 🐛 `1755344` fix(reports): reposiciona cfdi fuera del overflow-hidden, depura tabla cfdi y aplica paleta brand unificada a totales en factura/cotizacion/oc
- 🐛 `e6cbb78` fix(reports): correccion de anchos fijos en tabla cfdi, unificacion tipografica de totales y estandarizacion de layout en todos los reportes
- 🐛 `f076523` fix(invoice): correccion de anchos de columna en bloque cfdi forzando renderizado horizontal y alineacion estricta de totales
- 🐛 `2d0d8d5` fix(reports): unificacion visual factura/cotizacion - cfdi desbloqueado, totales limpios, descuento duplicado removido
- 🐛 `23e3cec` fix(invoice): recuperacion de variables qweb del cfdi 4.0 y correccion visual de la tabla de totales
- 🐛 `ba81f97` fix(invoice): resolucion de parseerror en xpath de columnas, implementando estrategia css posicional para ocultar codigo de producto y unidad
- 🐛 `6c5dcdf` fix(invoice): supresion columnas SAT (ClaveProdServ/ClaveUnidad), rediseno total y CFDI
- 🐛 `17dd90a` fix(invoice): eliminacion de columnas codigo/unidad para liberar layout, reconstruccion de totales y cfdi 4.0 en tablas
- 🐛 `038b459` fix(reports): recuperacion de diseño estable, correccion de factura y estandarizacion visual global de reportes
- 🐛 `b514474` fix(invoice): corrige montos, QR y supresion CFDI nativo en pdf
- 🐛 `4b54eb0` fix(invoice): refactorizacion de totales y cfdi 4.0 usando tablas para evitar colapso en renderizado de wkhtmltopdf
- 🐛 `7b338c6` fix(invoice): colgroup + inv-total-col + t-esc monetarios para totales correctos
- 🐛 `0ca35e4` fix(invoice): restaura tabla en totales con table-layout fixed para mostrar subtotal y total
- 🐛 `798794b` fix(invoice): reestructuracion grid de totales y bloque cfdi 4.0 para evitar desbordamiento en pdf
- 🐛 `f44469a` fix(invoice): restaura totales y contiene cadenas cfdi en pdf
- 🐛 `228ec92` fix(invoice): ajusta escala visual del pdf corporativo de factura
- 🐛 `8a79104` fix(invoice): elimina bloque fiscal nativo duplicado en pdf
- 🐛 `04a17f7` fix(invoice): estandarizacion del pdf de la factura replicando el diseño corporativo cfdi 4.0 y consolidacion de lotes
- 🐛 `10f91dc` fix(invoice): correccion de xpath en el header del layout wave para compatibilidad con odoo 19
- 🐛 `1cd406a` fix(invoice): evita xpath fragil en layout de factura
- 🐛 `6bff5c4` fix(invoice): replica layout pharma en vista customer invoices
- 🐛 `9986acd` fix(invoice): muestra lotes reales en columnas de factura
- 🐛 `2c9137c` fix(invoice): restaura columnas de lote y caducidad sin duplicar informacion
- 🐛 `205d483` fix(invoice): consolidacion de lotes en tabla principal y rediseño jerarquico del footer cfdi 4.0
- 🐛 `0d0d061` fix(invoice): eliminacion de qr duplicado y rediseño profesional del bloque fiscal cfdi 4.0
- 🐛 `50ca62f` fix(core): resolucion de warnings de acls/etiquetas y limpieza de datos fiscales duplicados en plantilla pdf de factura

## 2026-05-11

- 🐛 `347864b` fix(custom_invoice_format): lot/expiry purchase trace, drop dup address, compact
- 🐛 `9f460ca` fix(custom_invoice_format): add cfdi sat footer and align vendor lines
- 🐛 `7ca0345` fix(custom_invoice_format): remove pharma_invoice_hide_native_address_layout
- 🐛 `6cb0dbc` fix(custom_invoice_format): use verified xpath for address_layout override
- 🐛 `41396f0` fix(custom_invoice_format): load legacy address view neutralizer first
- 🐛 `fbe743d` fix(custom_invoice_format): neutralize legacy address-stripping template
- 🐛 `08e4943` fix(custom_invoice_format): preserve native invoice address nodes
- 🐛 `1e84080` fix(custom_invoice_format): clean invoice line bindings and uppercase thead
- 🐛 `fd0a3e2` fix(custom_invoice_format): align invoice header layout
- 🐛 `145ee52` fix(custom_invoice_format): use valid t-field in invoice address
- 🐛 `b46bbb3` fix(custom_invoice_format): update invoice report xpaths
- ✨ `1b2390e` feat(reports): standardize pharma layout across invoice/sale/purchase/delivery
- ✨ `d35c991` feat(account): customize vendor invoice report and list

## 2026-04-27

- • `7278fad` cleanup: add minimal content to empty __init__.py files

## 2026-04-20

- 🐛 `7c66e2c` fix(custom_invoice_format): robustece obtención de lote en columna Lote
- 🐛 `8f6ae3f` fix(custom_invoice_format): sustituye columna SAT duplicada por columna Lote
- 🐛 `567bba1` fix(custom_invoice_format): guarda existencia de campo para código SAT
- 🐛 `e79864b` fix(custom_invoice_format): oculta #informations y #right-elements vía CSS
- 🐛 `15202dd` fix(custom_invoice_format): revierte replace de t-set=address, usa CSS
- 🐛 `48ecb9a` fix(custom_invoice_format): prioridad 99 para evitar conflicto con POS
- 🐛 `0a46ed9` fix(custom_invoice_format): elimina RFC duplicado y mueve lotes a descripción
- 🐛 `d60305d` fix(custom_invoice_format): elimina bloques nativos con XPath replace, no con CSS
- 🐛 `37f5fb5` fix(custom_invoice_format): reubica totales, restaura CFDI box, corrige CSS y lotes
- 🐛 `895045c` fix(custom_invoice_format): elimina header duplicado, agrega lotes, corrige CSS
- 🐛 `05dfc72` fix(custom_invoice_format): elimina campo mobile inexistente en Odoo 19
- 🐛 `49e206d` fix(custom_invoice_format): usa partner_id.mobile en lugar de company_id.mobile
- 🐛 `142bbd1` fix(custom_invoice_format): reemplaza <t t-field> por <span t-field>
- 🐛 `f64c609` fix(custom_invoice_format): corrige XPaths a selectores reales de Odoo 19
- 🐛 `a7ed854` fix(custom_invoice_format): reemplaza position=prepend (inválido) por position=before
- 🐛 `7ab1211` fix(custom_invoice_format): reemplaza position=replace por XPaths aditivos
- ✨ `d715d99` feat(custom_invoice_format): nuevo módulo de formato de factura CFDI 4.0
