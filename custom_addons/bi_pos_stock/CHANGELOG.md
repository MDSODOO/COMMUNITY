# Changelog — bi_pos_stock

Historial generado automáticamente a partir de `git log -- bi_pos_stock`. No es prosa editorial: cada línea es un commit real. Mantener actualizado: después de modificar este módulo, anteponer la entrada nueva bajo la fecha de hoy (o crear el día si no existe).

**Commits registrados:** 114 | **Rango:** 2026-01-21 → 2026-06-14

---

## 2026-07-07

- 🐛 fix(bi_pos_stock): **URGENTE** — el fix de "Productos" (ver entrada siguiente) usaba `new Set(...)` dentro de una expresión QWeb; el compilador de OWL resuelve identificadores contra el contexto (`ctx`) del template y los constructores globales de JS (`Set`, `Map`, `Array`...) no están expuestos ahí. Causaba `OwlError: ctx.Set is not a constructor` y rompía el carrito COMPLETO en cualquier orden con al menos 1 producto (confirmado en vivo: pantalla en blanco al agregar el primer producto, apenas minutos después de desplegar el fix anterior). Reemplazado por `.filter((v, i, arr) => arr.indexOf(v) === i).length` — mismo resultado, sin constructores globales. Verificado en vivo sin errores de consola, tanto en venta normal de 1 producto como en el escenario de 2 lotes del mismo producto ("Productos: 1", "Piezas: 2.00").
- 🐛 fix(bi_pos_stock): el contador "Productos" del ticket/carrito usaba `props.order.lines.length` (renglones), así que el mismo producto repartido en 2 `pos.order.line` por llevar lotes distintos (`orderline_lot_patch.js` las mantiene separadas a propósito) se contaba como 2 productos, aunque el ticket ya las fusiona visualmente en 1 renglón. Ahora agrupa con la MISMA clave que usa `mergeReceiptLotLines` (producto+`price_unit`+`discount`; combos cuentan aparte por su propio `uuid`) y cuenta grupos distintos, no líneas. "Piezas" no cambia — sigue sumando `qty` de todas las líneas.
- ✨ feat(bi_pos_stock): la sección de "Lote" en el ticket ahora muestra `<cantidad> Lote <código> <fecha de caducidad>` (ej. "1 Lote 06ZN25 23/08/2030") en vez de solo `Lote <código>`. `lot_label_patch.js` (`PosOrderline.packLotLines`) arma el texto completo por línea de origen — cantidad = `this.qty` (una línea = un solo lote, por diseño de `orderline_lot_patch.js`), fecha = lookup en `pos.allLotDetails` (precargado por `get_all_lot_details()`, misma fuente que `lot_cascade_patch.js`) usando `formatExpiryDate()` de `lot_expiry_utils.js`. Como `PosOrderline` es un modelo de datos (no un componente OWL, no puede usar `usePos()`), se agregó `getPosStoreRef()` en `models.js` — una referencia global al `PosStore` activo, fijada en `processServerData()` — para que el getter llegue a `allLotDetails`. `OrderDisplay.mergeReceiptLotLines` (fusión visual de lotes) se simplificó: ya no anexa cantidad al texto del lote al fusionar, porque cada renglón ya trae la suya de fábrica.
- 🐛 fix(bi_pos_stock): badge de descuento no se mostraba en líneas con precio por pricelist — Odoo nunca llena `pos.order.line.discount` para descuentos de pricelist (solo el numpad lo hace, confirmado en `point_of_sale.assets_prod.min.js`/`ProductProduct.getPrice()`), así que ni el badge nativo ni `OrderlineInlineDiscount` (ambos leen `line.discount`) aparecían. Nuevo `orderline_discount_patch.js` (`PosOrderline.getEffectiveDiscountInfo()`) deriva el % comparando `price_unit` contra el `lst_price` real cuando `discount===0`. Ver `docs/audits/2026-07-02_pricelist_discount_architecture.md` §4d.

## 2026-07-04

- 🐛 fix(bi_pos_stock): la fusión visual de lotes mostraba solo la cantidad total consolidada, sin la cantidad de cada lote individual. Cada `Lote X` ahora muestra `: N` con la cantidad propia de su línea de origen (válido porque `orderline_lot_patch.js` garantiza un único lote por `pos.order.line`, así que `data-line-qty` de esa línea ES la cantidad de ese lote). Verificado en vivo: "Lote H24T200: 1" / "Lote H25S227.: 1" con cantidad total "2" y precio "$97.04" correctos.
- ✨ feat(bi_pos_stock): fusión visual de lotes en el ticket — cuando el mismo producto (mismo `price_unit`/`discount`) queda repartido en varias `pos.order.line` por llevar lotes distintos, el ticket impreso las muestra como un solo renglón con la cantidad y el precio sumados, y el desglose de lote debajo (`Lote A`, `Lote B`, ...). `orderline_lot_patch.js` sigue manteniendo las líneas separadas en `order.lines`/carrito a propósito (trazabilidad de inventario/reportes intacta) — la fusión es puramente visual, post-render, sobre el DOM del ticket (`OrderDisplay.mergeReceiptLotLines`, `order_widget.js`), sumando `line.qty`/`line.displayPrice` ya calculados por Odoo (no reimplementa impuestos/descuentos). Se apoya en atributos `data-merge-key`/`data-line-qty`/`data-line-price` agregados vía XPath sobre `point_of_sale.Orderline` (solo agrega atributos, no reestructura nada nativo). Verificado en vivo con Playwright: 2 líneas en el carrito → 1 renglón fusionado en el ticket con cantidad (2), precio ($253.14 = $126.57×2) y ambos lotes correctos, sin errores de consola.
- 🐛 fix(bi_pos_stock): negro sólido + negrita en todo el ticket para impresión térmica — texto con `font-weight` normal o grises (`#555`/`#333`/`.text-muted` de Bootstrap) se veía descolorido/irregular en la impresora física. Se fuerza `color:#000 !important; font-weight:bold !important;` sobre `.pos-receipt` y todos sus descendientes (gana incluso a utilidades de Bootstrap con su propio `!important`), y los bordes punteados pasan de `#ccc` a negro. Declaraciones de color/peso por elemento que quedaron redundantes, removidas.
- 🐛 fix(bi_pos_stock): `lot_label_patch.js` — "Lote"/"NS" en vez del "Lot Number"/"SN" que Odoo core hardcodea en inglés dentro del getter `packLotLines` (no envuelto en `_t()`, no hay `.po` que lo traduzca); se sobreescribe el getter completo. Línea "Ahorro: X%..." reducida de 11px a 9px; `.lot-number` ya no fuerza 11px, hereda los 9px de `.info-list` para verse consistente con el resto de renglones pequeños del ticket.

## 2026-07-03

- ✨ feat(bi_pos_stock): rediseño de ticket — nombre de caja antes de "Atendido por", descuentos consolidados, footer sin marca Odoo. Verificado contra el código fuente real de Odoo 19 (`.cashier`/`.pos-receipt-contact` viven en `point_of_sale.ReceiptHeader`, componente hijo de `OrderReceipt`; variable de contexto real es `order`, no `receipt`). Cambios: `order.config.name` (nombre de caja, no `order.company.name` — ese es la persona física del RFC, no presentable) en negrita antes del cajero (`ReceiptHeaderCompanyName`, target `point_of_sale.ReceiptHeader`); línea "Ahorro: X% (Precio orig: $Y)" reemplaza el badge "Dto:" anterior (`OrderlineInlineDiscount`, sin tocar target ni cálculo); `.price-per-unit` oculta vía CSS — esa clase la reutiliza `point_of_sale.Orderline` nativo tanto para "$X / Unidades" como para su propia línea de descuento con ícono `fa-tag`, así que un solo hide quita ambas; footer nativo (sucursal/dirección/RFC/email/website, duplicado con el header) oculto vía CSS con `!important` (Bootstrap 5 define `.d-flex` con `!important`, que gana sobre un `display:none` normal); "Powered by Odoo" (`.footer-powered-by`) eliminado por XPath; email/website reinsertados centrados a 12px. 2 bugs reales encontrados y corregidos en verificación en vivo con Playwright: el hide de `.pos-receipt-contact` también ocultaba el div nuevo del nombre de caja (mismo selector sin excluirlo — se le dio clase propia `.md-receipt-company-name`), y el hide del footer no tenía efecto por el `!important` de Bootstrap.
- 🐛 fix(bi_pos_stock): `OwlError: cannot be located in element tree` al abrir el ticket del PoS — `order_receipt.xml` heredaba `point_of_sale.OrderReceipt` buscando `.order-container`, pero esa clase vive en el arch del componente hijo `point_of_sale.OrderDisplay` (invocado por OrderReceipt), no en el de OrderReceipt mismo; `t-inherit` no puede ver dentro de un componente hijo. Corregido a `t-inherit="point_of_sale.OrderDisplay"`, mismo patrón que `order_widget.xml` (que ya apuntaba correctamente a `.order-summary` en ese componente). Efecto colateral: el encabezado "Producto | Precio" ahora también aparece en el carrito de ProductScreen, igual que `.md-order-stats`.
- ✨ feat(bi_pos_stock): reformato del ticket de cliente (OrderReceipt) para impresión térmica 80mm — tipografía monoespaciada, separadores punteados entre secciones, encabezado de columnas "Producto | Precio" (`generic_components/order_receipt/order_receipt.xml`), y aplanado de las tarjetas bento `.md-order-stats`/`.md-order-stat` a texto plano solo dentro de `.pos-receipt` (`scss/pos_receipt_print.scss`) — el estilo bento a color se conserva sin cambios en el carrito de ProductScreen. No hay IoT Box configurada (confirmado vía `pos_ping_silence.js`), así que el ticket físico sale por impresión de navegador sobre este mismo DOM/CSS. Pendiente de commit.
- ✨ feat(bi_pos_stock): botón "Actualizar precios" en navbar del PoS — refresca `product.pricelist`/`product.pricelist.item` vía `pos.data.searchRead()` sin cerrar sesión. Corrige que el descuento no se viera en clic directo cuando la sesión llevaba abierta desde antes de crear el pricelist item (ver `docs/audits/2026-07-02_pricelist_discount_architecture.md` §4c). Pendiente de commit.

## 2026-06-14

- ✨ `26bbb52` feat(bi_pos_stock): dark mode completo en tarjetas POS y rightpane
- 🐛 `8290c25` fix(bi_pos_stock): color base de texto para pantallas y modales en dark mode
- ✨ `fc89441` feat(bi_pos_stock): dark mode selectivo para pantallas full-screen y modales

## 2026-06-13

- 🐛 `cc3110b` fix(dark-mode): eliminar dark mode POS + forzar statusbar scrap_batch oscuro
- 🐛 `cb6c816` fix(dark-mode): pos-force-light para iface_theme + statusbar scrap_batch en dark mode
- 🐛 `c382591` fix(dark-mode): migrar dark mode de scrap_batch a bundle web.assets_web_dark + fix texto tarjetas POS
- 🐛 `526ce49` fix(bi_pos_stock): corregir dark mode POS usando prefers-color-scheme
- 🐛 `2690a95` fix(bi_pos_stock): adaptar tarjetas de producto y botones del POS al modo oscuro en v19

## 2026-06-10

- • `998e73f` improvement(bi_pos_stock): rediseño bento — pill tabs, bento tables, stat tiles v19.0.6.7
- • `d8d9b78` improvement(bi_pos_stock): colores a variables CSS, liquid glass en modales y gradiente en headers
- • `1060f46` improvement(bi_pos_stock): mejorar UI/UX de botones y aplicar colores corporativos
- 🔧 `12d476b` chore(global): xml headers, cobertura de tests en 5 módulos y limpieza de TODOs
- ✨ `6256359` feat(global): agregar i18n/es_MX.po a 11 módulos

## 2026-06-03

- ✨ `9d54982` feat(pos): redireccion de boton en closepospopup para descargar nuevo reporte de cierre de caja
- 🐛 `6c68890` fix(pos): saltos de página y layout Devoluciones corregidos
- 🐛 `f012c88` fix(pos): colores de card-head, Devoluciones 3 cols y page-break sin blancos
- 🐛 `b04d8fc` fix(pos): eliminacion de referencia a reporte obsoleto point_of_sale.pos_session_sales_details_report que bloqueaba la instalacion
- ✨ `cb2c810` feat(corte-z): Cierre de Caja como único reporte de pos.session + fix dirección duplicada
- 🐛 `da37c1f` fix(corte-z): corregir espaciado en pagina resumen y color de barra teal
- 🐛 `8ecd7a4` fix(pos-report): encabezados visibles, layout facturas y mayusculas en Cierre de Caja
- 🐛 `9fcce7e` fix(pos-report): corregir saltos de pagina y layout del Cierre de Caja
- 🔄 `f029a32` refactor(pos): eliminacion de reporte global redundante, desactivacion de envio automatico en corte de caja y estandarizacion qweb del reporte a la mano

## 2026-06-02

- 🐛 `bc187d7` fix(pos): normalizar etiquetas visibles a A la mano

## 2026-06-01

- • `d966ea1` improvement(backend): sistema de design tokens y refactor UI Bento-box (29 mejoras)
- • `6128707` improvement(bi_pos_stock): amplia nuevamente tipografia de cierre de caja para mayor legibilidad
- • `fdca0fb` improvement(bi_pos_stock): aumenta tipografia y espaciado para legibilidad en reportes pdf
- 💄 `46c8708` style(bi_pos_stock): optimizacion responsiva, table-responsive y escalado de fuentes para lectura movil de reportes
- • `75a90ad` improvement(bi_pos_stock): optimizacion responsiva, table-responsive y escalado de fuentes para lectura movil de reportes
- ✨ `c779ee0` feat(reports): integracion de layout bento-box y glassmorphism adaptado para wkhtmltopdf en el Reporte Global del dia
- ✨ `e232dd7` feat(pos): desglosa cierre global por usuario y sucursal
- 🐛 `58e6e2c` fix(pos): alinea resumen global con layout de cierre de caja
- ✨ `66cd5a9` feat(pos): fix corte z sizing and add resumen global dia report
- ✨ `7281080` feat(cierre-caja): renombra Corte Z y fusiona info faltante del reporte nativo
- 🐛 `0c99a6f` fix(corte-z): reinyecta charset utf-8 para evitar mojibake en PDF
- 🐛 `04d65be` fix(pos): corrige totales e impuestos del reporte corte z
- ✨ `d7c4546` feat(pos): Corte Z PDF horizontal (A4) con diseno Bento desde pos.session

## 2026-05-29

- 🐛 `14e7f5e` fix(backend): renombrar qty_available→qty_on_hand y sincronizar vista XML para crear tablas DDL en bi_pos_stock

## 2026-05-27

- 🐛 `7de40da` fix(core): reubicacion de variables de traduccion en portal controller, fix de dependencias en medicine_depot_portal y asignacion de _name en modelo de picking

## 2026-05-26

- 🐛 `4ec3c32` fix(bi_pos_stock): corregir parent del menuitem Inventario BF para Odoo 19
- ✨ `09f0022` feat(bi_pos_stock): integración de inventario BF + headers de mes dinámicos

## 2026-05-20

- ✨ `164edfa` feat(bi_pos_stock): mejoras UI/UX, caducidades FEFO y correcciones de consola

## 2026-05-18

- 🐛 `cedce98` fix(fase-1): eliminar CDN externa y homologar terminología "A la mano" en vistas de admin
- 🔧 `eddf255` chore(bi_pos_stock): eliminar XML comentado de server actions del Reporte Z

## 2026-05-14

- 🐛 `31d7216` fix(core): resolucion de acls deprecados en modulos de stock, eliminacion de herencia fantasma y override xml para etiquetas de studio
- 🐛 `8e7c2f2` fix(global): auditoría de rama test y aplicación de correcciones críticas nivel 1 (acls, sintaxis y dependencias)

## 2026-05-12

- 🐛 `33eaf3f` fix(pos): refactorizacion de response en controlador de stock para evitar crash en service worker

## 2026-05-11

- • `48b47e8` improvement(bi_pos_stock): show product line in inventory
- 🐛 `4dfa287` fix(bi_pos_stock): preload studio lines and bypass pos cache
- 🐛 `f16d0c0` fix(bi_pos_stock): scope inventory history by branch

## 2026-05-09

- 🐛 `8fc8da1` fix(bi_pos_stock): quarterly sales bug + SW TypeError + tab uniformity
- 🐛 `d4e7883` fix(bi_pos_stock): sales calculation bug + UI standardization
- 🐛 `5f0c915` fix(bi_pos_stock): add static props to EcommerceOrdersScreen
- ✨ `6242c4a` feat(bi_pos_stock): Excel export from Stock screen (replaces PDF)
- ✨ `e654b5a` feat(bi_pos_stock): barcode column, contrast fix, PDF export

## 2026-05-08

- 🐛 `faea574` fix(bi_pos_stock): migrate read_group to _read_group (Odoo 19) + add static props
- 🔄 `426a8f8` refactor(bi_pos_stock): unify stock tabs, monthly sales split, name formatting, terminology

## 2026-05-06

- 🔧 `d9dedae` chore(.gitignore): remove .claude/ and .DS_Store from tracking

## 2026-05-04

- 🐛 `5af39ed` fix(bi_pos_stock): migrate _compute_branch_stock to _read_group
- 🐛 `6a57bc8` fix(bi_pos_stock): align z report sender with smtp filter
- 🔧 `e471387` chore(bi_pos_stock): remove z report validation actions
- ✨ `c97f688` feat(bi_pos_stock): consolidate z report by pos day
- ✨ `7e2da6f` feat(bi_pos_stock): classify invoice type in z report excel
- ✨ `d70cfad` feat(bi_pos_stock): add order customers to z report summary
- 🐛 `e07ef35` fix(bi_pos_stock): clarify pos order customer in z report
- ✨ `b642d61` feat(bi_pos_stock): add z report excel download action
- ✨ `ce1d680` feat(bi_pos_stock): email z report as excel
- 🐛 `7106d8f` fix(bi_pos_stock): update pos sales details pdf
- ✨ `4fce6f6` feat(bi_pos_stock): add z report preview action
- ✨ `b535bdc` feat(bi_pos_stock): add pharma z report email

## 2026-04-22

- • `2b8a83d` audit: Odoo 19 / Odoo.sh compatibility fixes and performance optimizations

## 2026-04-18

- 🐛 `5a5246a` fix(bi_pos_stock): cashier_display sin store para evitar UndefinedColumn en Odoo.sh
- ✨ `cd8d47a` feat(bi_pos_stock): restaura columna Cajero en vista lista de pos.order

## 2026-04-17

- 🐛 `b4823f2` fix(security): resuelve AccessError en stock.warehouse para usuarios sin acceso
- 🐛 `04e41a9` fix: corrige TypeError taxes_id en cascada de lotes POS y deprecation type='json'
- ✨ `3fd10b5` feat(bi_pos_stock): cascada automática de lotes al superar stock de lote
- ✨ `8f78827` feat: lotes como líneas separadas en POS + fix propagación de lotes en OC

## 2026-04-15

- 🔧 `d56d6cc` chore: actualiza autor y website en manifests de módulos personalizados

## 2026-04-13

- 🐛 `0db25dd` fix: bi_pos_stock — reemplazar self._cr por self.env.cr (deprecado en Odoo 19)

## 2026-04-08

- 💄 `ed896b8` style: hide native product-cart-qty badge on ProductCard
- 💄 `58a24ed` style: adjust POS order summary colors/sizes + lot info icon color

## 2026-04-07

- ⚡ `4248f19` perf: optimize POS session load + prevent order loss on screensaver (v19.0.5.0)
- 🐛 `3f7e47a` fix: traffic-light stock badge + upgrade crash fix (v19.0.4.3)

## 2026-04-06

- ✨ `5b49fbc` feat: show selected-lot expiry+qty on ProductCard footer (v19.0.4.2)
- ✨ `a7453b2` feat: widen leftpane + enlarge product cards for FEFO badges (v19.0.4.1)
- ✨ `f4b8fb1` feat: FEFO lot expiry visibility in POS — badges, guide table, detail popup (v19.0.4.0)
- ✨ `87558a6` feat: replenishment screen with quarterly sales + ecommerce order notifications (v19.0.3.1)
- ✨ `d786111` feat: replenishment screen connected to stock.warehouse.orderpoint (v19.0.3.0)
- 🐛 `3392af5` fix: 3 bugs in bi_pos_stock and custom_shop_qty_selector (v19.0.2.2)
- ✨ `f47d4da` feat: low stock screen shows top-sold products with low branch stock (v19.0.2.1)
- ✨ `d3a1c3e` feat: enforce branch stock limit on numpad and +/- qty changes in bi_pos_stock (v19.0.2.0)

## 2026-04-05

- 🐛 `c25ec0f` fix: stock badges — mirror core productCartQty pattern exactly (v19.0.3)
- 🔄 `df52b4d` refactor: stock badges via PosStore.stockByTmplId instead of prop chain (v19.0.2)
- 🐛 `7647467` fix: stock badge display — template XPath and branchStock iteration (v19.0.1.2)
- 🐛 `43b76b8` fix: LowStockProducts template 'ui.isSmall' undefined error
- 🐛 `6c67429` fix: stock badge display and Low Stock navigation (v19.0.1.1)
- 🐛 `a85fc07` fix: corregir errores OWL lifecycle en order_widget y product_list
- 💄 `0471225` style: separar totales en líneas independientes en order_widget
- 🐛 `8c40444` fix: revertir _load_pos_data_fields en PosConfig — rompe carga estándar
- 🐛 `7b581e4` fix: corregir API de navegación y campos config POS (Odoo 19)
- 🐛 `0ff49dd` fix: corregir 5 bugs críticos en bi_pos_stock (v19.0.1.1)
- 🔄 `d6ddc03` refactor: multi-branch POS stock security & architecture (v19.0.1.0)

## 2026-04-04

- 🔄 `401e0f6` refactor: multi-branch POS stock security & architecture (v19.0.1.0)
- 🔄 `a5412e5` refactor: multi-branch POS stock security & architecture (v19.0.1.0)
- 🔄 `d316253` refactor: multi-branch POS stock security & architecture (v19.0.1.0)
- 🔄 `16ce95f` refactor: multi-branch POS stock security & architecture (v19.0.1.0)
- 🔄 `d1ccd19` refactor: multi-branch POS stock security & architecture (v19.0.1.0)

## 2026-04-02

- • `6a7b895` Fix bi_pos_stock and pos_order_transfer for Odoo 19
- 🐛 `89da95f` fix(pos): stock display and order transfer for Odoo 19

## 2026-04-01

- 🐛 `25746c7` fix(pos): fix bi_pos_stock crash and add pos_order_transfer module
- • `675b534` [bi_pos_stock] Fix stock display per branch with lot/quant accumulation
- 🐛 `2478cc4` fix(bi_pos_stock): corregir clave de template ID y acumulación de lotes
- 🐛 `0325a89` fix(bi_pos_stock): corregir validateProps y key incorrecto en ProductCard
- 🐛 `006b21b` fix(bi_pos_stock): corregir stock por sucursal y agregar contador de piezas

## 2026-01-21

- • `d9efbaf` Addon pos_stock
