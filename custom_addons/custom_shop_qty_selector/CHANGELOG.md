# Changelog — custom_shop_qty_selector

Historial generado automáticamente a partir de `git log -- custom_shop_qty_selector`. No es prosa editorial: cada línea es un commit real. Mantener actualizado: después de modificar este módulo, anteponer la entrada nueva bajo la fecha de hoy (o crear el día si no existe).

**Commits registrados:** 92 | **Rango:** 2026-04-05 → 2026-06-29

---


## 2026-07-03

- ✨ `(pendiente commit)` feat(custom_shop_qty_selector): badge de % de descuento también en la PDP (`product_detail_discount_badge`, hereda `website_sale.product`, ancla `o_wsale_product_images` — ya usada en `medicine_depot_website`). Reutiliza `.o_md_discount_badge` (mismo pill del grid) y `combination_info` (la misma fuente que ya usa el precio tachado en la PDP, distinto de `template_price_vals` que usa el grid).
- ↩️ `(pendiente commit)` revert(custom_shop_qty_selector): se quita la cintilla de descuento (`products_item_discount_ribbon`, `.o_md_discount_ribbon`) agregada hace unos commits — a pedido explícito, se mantiene únicamente el pill de la esquina de la imagen (`.o_md_discount_badge`).
- 🐛 `(pendiente commit)` fix(custom_shop_qty_selector): el badge `.o_md_discount_badge` y la cintilla `.o_md_discount_ribbon` quedaban con fondo transparente (invisibles) pese a `background: var(--bs-danger)` — verificado en vivo con getComputedStyle: esas custom properties de Bootstrap no resuelven en este frontend (el build de Odoo no las expone a este scope), aunque las clases utilitarias de Bootstrap como `.text-danger` sí funcionan (compiladas con el color embebido). Fix: usar el hex literal `#dc3545` (mismo rojo confirmado vía `.text-danger`) en vez de la custom property.
- ✨ `(pendiente commit)` feat(custom_shop_qty_selector): cintilla de descuento en el tope de la card del grid (`.o_md_discount_ribbon`, `products_item_discount_ribbon`) — banner horizontal de ancho completo con "X% de descuento", distinto y adicional al pill `.o_md_discount_badge` que ya vive en la esquina de la imagen. Radio de esquinas superiores igual al de la card bento (`md_bento_theme/static/src/scss/md_shop.scss`).
- ✨ `(pendiente commit)` feat(custom_shop_qty_selector): filtros "Ingrediente Activo" y "Línea" ordenados por popularidad de venta (unidades vendidas en POS + ventas en línea, últimos 90 días — `_md_get_sales_popularity`/`_md_get_relation_popularity_score`) en vez de alfabético; empate/sin ventas cae a alfabético como desempate. Se combina POS y web porque la mayoría de las ventas de esta farmacia ocurren en mostrador, no en el sitio. Agrega dependencia `point_of_sale` al manifest (antes no declarada, aunque siempre estuvo instalada en este entorno).
- 🐛 `(pendiente commit)` fix(custom_shop_qty_selector): los 3 filtros custom (Ingrediente Activo, Línea, Descuentos Especiales) nunca filtraban el listado de productos de `/shop`, solo el conteo del sidebar y el rango de precio — causa raíz más profunda que el bug de JS: `WebsiteSale._get_shop_domain` NO se usa para el listado real en Odoo 19 (verificado contra el código fuente); `_shop_lookup_products` usa `website._search_with_fuzzy(...)` → `product.template._search_get_detail(website, order, options)`, con `options` construido por `_get_search_options`. Fix: nuevo override de `_get_search_options` en el controlador (resuelve los 3 filtros a fragmentos de dominio simples) + nuevo `_search_get_detail` en `models/product_template.py` (los aplica a `base_domain`). El código existente en `_get_shop_domain` se deja intacto — sigue siendo válido para el rango de precio y el conteo de atributos.
- 🐛 `(pendiente commit)` fix(custom_shop_qty_selector): `_md_discounted_template_ids` (filtro "Descuentos Especiales") tiraba 500 — `request.website.get_current_pricelist()` no existe en Odoo 19 (verificado en vivo con el traceback real del sitio de prueba). El método correcto es la propiedad `request.pricelist`, armada vía `lazy()` en `website_sale`'s `ir_http._pre_dispatch` y siempre disponible en cualquier controlador de website_sale — ver `addons/website_sale/models/ir_http.py` línea 34 y `models/website.py::_get_and_cache_current_pricelist`.
- 🐛 `(pendiente commit)` fix(custom_shop_qty_selector): los filtros custom de la barra lateral (Ingrediente Activo, Línea, Descuentos Especiales) no funcionaban — cualquier clic los descartaba en silencio. Causa raíz verificada contra el código fuente real de Odoo 19 (`addons/website_sale/static/src/interactions/website_sale.js`): el listener nativo `onChangeAttribute`, delegado sobre todo `input`/`select` dentro de `form.js_attributes`, reconstruye la URL desde cero usando solo `attribute_value`/`tags` y descarta cualquier otro nombre; el `onchange="this.form.requestSubmit()"` inline que estos filtros usaban entraba en carrera con ese listener y siempre perdía. Fix: se quitó el `onchange` inline de los 3 filtros y se agregó `static/src/js/shop_filters_patch.js` (parcha `onChangeAttribute` vía `patch()` de OWL para reconocer también `active_ingredient`/`product_line`/`discount_tier`, con semántica de parámetro repetido consistente con `request.httprequest.args.getlist()` en el backend).

## 2026-07-02

- 💄 `(pendiente commit)` style(custom_shop_qty_selector): color rojo semántico (`var(--bs-danger)`) para el badge de % de descuento del grid y el precio original tachado, tanto en el grid (`products_item_discount_price_red`) como en la PDP (`product_price_red_strikethrough`, hereda `website_sale.product_price`, ancla verificada `span[@name='product_list_price']`).
- ✨ `(pendiente commit)` feat(custom_shop_qty_selector): badge de % de descuento en el grid de la tienda (`products_item_discount_badge`, basado en `template_price_vals['base_price']`/`['price_reduce']`, no en `combination_info` que es exclusivo de la PDP), detalle de ahorro por línea en el carrito (`cart_line_savings`, hereda `website_sale.cart_lines_price`), y filtro lateral "Descuentos Especiales" por rango 0-5%/5-10% (`discount_tier` GET param resuelto contra `product.pricelist.item` vigentes del pricelist activo del sitio, ver `docs/audits/2026-07-02_pricelist_discount_architecture.md`). Ver `docs/modules/custom_shop_qty_selector.md`.

## 2026-07-01

- 🐛 fix(custom_shop_qty_selector): completar el fix de company_id — quedaba una segunda ocurrencia del mismo bug en el domain de `stock.quant` (`_md_lot_filtered_available_qty`) y en `_lot_filtered_stock_qty_map`, ambas seguían usando la compañía de sesión/website en vez de la del warehouse resuelto; verificado tras deploy asignando temporalmente x_studio_branch_office=Cancún al admin de prueba
- 🐛 fix(custom_shop_qty_selector): usar company_id del warehouse resuelto (no el de la sesión/website) al filtrar ubicaciones internas — evita que sucursales con stock real muestren "Sin producto a la mano" cuando el warehouse de la sucursal pertenece a una `res.company` distinta a la de la sesión

## 2026-06-29

- 🐛 `5004b6e` fix(custom_shop_qty_selector): stock web visible solo para usuarios B2B autenticados

## 2026-06-27

- 🐛 `823e937` fix(website-stock): aplicar filtro de sucursal en SSR y suma de lotes en similares

## 2026-06-19

- 🐛 `6359398` fix(custom_shop_qty_selector): prevenir operacion de escritura no autorizada en product.template que bloqueaba el boton de compra en el eCommerce

## 2026-06-11

- 🐛 `e360524` fix(custom_shop_qty_selector): usar requestSubmit en filtros custom del shop
- 🐛 `a6cdd88` fix(custom_shop_qty_selector): preservar nodo de disponibilidad nativa
- 🐛 `a5d10af` fix(custom_shop_qty_selector): evitar duplicado de disponibilidad en PDP
- 🐛 `b5b1e3c` fix(custom_shop_qty_selector): evitar doble condicion en template de disponibilidad
- 🐛 `3040326` fix(medicine_depot_website): corregir render de inventario y cantidad en ecommerce
- 🐛 `7b4fd09` fix(medicine_depot_website): corregir ruteo y renderizado de filtros de categorías y atributos en el shop

## 2026-06-10

- 📚 `678aa01` docs(global): auditoria de modulos, actualizacion de documentacion, propuesta de engine v2 y estructura inicial de manuales visuales para usuarios

## 2026-06-08

- 🐛 `3542ec4` fix(website): restaurar cards de productos al estado de main
- 🧪 `a7f4fb5` test(website): implementacion de auditoria playwright y restauracion de layout global navbar y shop desde main
- 🐛 `ab47803` fix(medicine_depot_portal): restaurar estilos de botones/cards de main y agregar carrito al navbar Bento

## 2026-06-03

- 🔄 `b12ee4b` refactor(web): separar capas web medicine depot

## 2026-06-02

- 🔄 `6d7ac99` refactor(ui): auditoria automatizada via playwright e implementacion de correcciones estructurales bento-box en vistas publicas
- 🐛 `a170d7a` fix(shop): controles de tarjeta mas compactos y a la misma altura
- 🔄 `855a187` refactor(shop): limpieza de scss del catalogo, reset de grid bento y optimizacion ergonomica de botones
- ✨ `9635b34` feat(ecommerce): badge a la mano como overlay sobre la imagen + 5 microinteracciones en tarjetas bento
- 🐛 `86373c4` fix(core): resolucion de attribute error forzando carga de modelo e implementacion de bloqueo anti-doble-clic para evitar concurrent update en sale_order
- ✨ `643cca2` feat(ecommerce): unificar etiqueta a la mano por sucursal (numero + pzs, rojo agotado) y emparejar tarjetas bento
- 🐛 `bc187d7` fix(pos): normalizar etiquetas visibles a A la mano
- 🐛 `cbd3cf2` fix(frontend): ejecutar mejoras criticas de auditoria ui ecommerce

## 2026-06-01

- ✨ `899bad2` feat(ui): ejecucion del plan de 69 mejoras UI/UX (login, sucursales, tienda, portal)

## 2026-05-27

- ✨ `8deb77e` feat(medicine_depot_website): redesign public UI surfaces
- ✨ `41cf3fc` feat(website): apply full 10-phase improvement plan (security, bugs, refactor, i18n, perf, scss, frontend, tests)

## 2026-05-20

- 🐛 `26c12a3` fix(custom_shop_qty_selector): usar notificacion nativa stock en PDP
- 🐛 `555faa3` fix(website): use native agotado UI with orange warning and wishlist active
- ✨ `bfafe53` feat(website): wishlist notifier legend for out-of-stock products
- ✨ `6a88abc` feat(website): filtra lotes con caducidad >6 meses en stock ecommerce

## 2026-05-18

- 🐛 `77c6cab` fix(custom_shop_qty_selector): reemplazar xpath //a generico por selector especifico

## 2026-05-14

- 🔧 `bbc6105` chore(core): migración segura de rama test a main - auditoría completa + fixes críticos
- 🐛 `8e7c2f2` fix(global): auditoría de rama test y aplicación de correcciones críticas nivel 1 (acls, sintaxis y dependencias)

## 2026-05-12

- ✨ `ba064a9` feat(core): migracion fase 3 - oleada 2 - medicine_depot_portal, custom_shop_qty_selector
- 🐛 `b97434f` fix(ui): inyeccion de nodo fantasma para wishlist navbar y estabilizacion de colibri js
- 🐛 `9ee5a77` fix(shop): sanear base_unit_count antes del schema sync
- 🔧 `6426aeb` chore(core): saneamiento de bd para base_unit_count y fix de deprecaciones
- 🐛 `76cdb6e` fix(shop): blindar migraciones de qty selector
- 🐛 `ab1c6ee` fix(core): harden main deployment migrations and portal
- 🐛 `575107e` fix(core): estabilizacion general y resolucion de conflictos post-merge
- 🐛 `7917f58` fix(shop): correccion de tabla para columna barcode en script de migracion
- 🐛 `b40dd52` fix(shop): correccion de tabla para columna barcode en script de migracion
- 🐛 `9ef7114` fix(shop): resolucion de access denied en product template
- 🐛 `95c49e1` fix(shop): resolucion de access denied en product template
- 🐛 `434fbb2` fix(custom_shop_qty_selector): backport studio acl post_init_hook from main
- 🐛 `431bcf3` fix(custom_shop_qty_selector): move studio acl creation to post_init_hook
- ✨ `0ef4f2e` feat(release): sync custom_shop_qty_selector, medicine_depot_portal, bi_pos_stock, custom_invoice_format from test
- 🐛 `f63d86d` fix(portal): js crash fix, centered cards and bento pdp redesign
- 🐛 `797889c` fix(shop): fit-content en pill de cantidad y logica backend multi-select para filtros

## 2026-05-11

- 🐛 `2ea9f3f` fix(shop): implementacion de logica backend para filtros custom de linea e ingrediente
- 🐛 `313fa9e` fix(shop): restauracion de logica js_attributes en filtros laterales
- • `eb511ea` improvement(shop): escalado de imagenes, fix de contador, inyeccion de linea y rediseno de filtros
- 🐛 `8100e6f` fix(shop): reestructuracion flexbox de pill y logica de atributos
- 🐛 `090b5dc` fix(shop): correccion visual de pill de cantidad y logica de filtros
- ✨ `ff52a7e` feat(shop): nuevo filtro linea, unificacion de botones y background premium
- 💄 `e62985d` style(shop): filtros colapsados por defecto y controles de tarjeta estilizados
- 🔄 `66d7780` refactor(shop): dinamismo en filtros, fix pill cantidad y mejora de PDP
- ✨ `5d5b5b0` feat(shop): UI/UX premium y sticky sidebar para filtros
- • `732c637` improvement(custom_shop_qty_selector): unify and flatten shop filters sidebar
- 🔄 `193adb9` refactor(shop): optimizacion responsiva de cards y filtros laterales
- 🔄 `0eb0da5` refactor(shop): modernize product cards and detail view
- 🐛 `fbe2952` fix(shop): stabilize wishlist js and ingredient filters
- 🐛 `663e308` fix(custom_shop_qty_selector): drop @title anchor on offcanvas clear-filters xpath
- 🐛 `6fe6f0b` fix(custom_shop_qty_selector): anchor active_ingredient_filter_form to the lone <form>
- 🐛 `ef3acae` fix(custom_shop_qty_selector): correct h6 to h2 in products_item XPath anchor
- ✨ `3bcf746` feat(custom_shop_qty_selector): add active ingredient shop filters
- • `f2c884f` improvement(custom_shop_qty_selector): refine product action button scale
- • `f720b80` improvement(custom_shop_qty_selector): fix add to cart button sizing
- • `1923238` improvement(custom_shop_qty_selector): qty starts at 0, floating wishlist, "A la mano"

## 2026-04-30

- 🐛 `ee54097` fix(custom_shop_qty_selector): sudo free_qty en product detail (403 público)

## 2026-04-23

- 🐛 `e81cd01` fix: resolve MRO conflict preventing portal orders from appearing
- ✨ `cca1f20` feat: implementación de visibilidad de órdenes con picking en portal Odoo 19

## 2026-04-22

- 🐛 `f1ba651` fix: vertical alignment of product cards in e-commerce grid (Odoo 19 audit)
- • `2b8a83d` audit: Odoo 19 / Odoo.sh compatibility fixes and performance optimizations

## 2026-04-20

- 🐛 `33670e2` fix(custom_shop_qty_selector): CTA estático y oculto en productos sin existencia
- 🐛 `bf421ab` fix(custom_shop_qty_selector): hover-reveal CTA, cards altura uniforme, widget PZA
- 🔄 `7613867` refactor(custom_shop_qty_selector): reemplaza widget +/- por select nativo
- 🐛 `5671aeb` fix(custom_shop_qty_selector): corrige cadena flex rota y elimina XPaths frágiles

## 2026-04-17

- 🐛 `b4823f2` fix(security): resuelve AccessError en stock.warehouse para usuarios sin acceso
- 🐛 `04e41a9` fix: corrige TypeError taxes_id en cascada de lotes POS y deprecation type='json'

## 2026-04-15

- 🔧 `d56d6cc` chore: actualiza autor y website en manifests de módulos personalizados

## 2026-04-07

- 🐛 `2829771` fix: card alignment + portal order visibility (v19.0.2.3.0)

## 2026-04-06

- 🐛 `3392af5` fix: 3 bugs in bi_pos_stock and custom_shop_qty_selector (v19.0.2.2)

## 2026-04-05

- 🐛 `2411a21` fix: enforce column layout via Bootstrap class + connect Add-to-Cart to qty selector (v19.0.2.1.0)
- 🐛 `f216d01` fix: guarantee badge+qty above Add-to-Cart using position=replace
- 🔄 `a245382` refactor: native Odoo qty style + move badge/qty below price
- 🔄 `ce943fc` refactor: merge custom_product_availability into custom_shop_qty_selector
- 🐛 `57d3339` fix: review and patch both availability modules
- ✨ `a5930ee` feat: add branch stock availability badge to shop product cards
- 🔄 `84f5379` refactor: qty selector static pill above Add to Cart button
- 🐛 `29e3248` fix: use contains(@t-attf-class) XPath since oe_product_image uses t-attf-class
- 🐛 `8cce74c` fix: correct XPath target in custom_shop_qty_selector templates
- ✨ `ad82af6` feat: add custom_shop_qty_selector module (v19.0.1.0.0)
