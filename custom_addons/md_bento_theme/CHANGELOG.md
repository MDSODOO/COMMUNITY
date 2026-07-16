# Changelog — md_bento_theme

Historial generado automáticamente a partir de `git log -- md_bento_theme`. No es prosa editorial: cada línea es un commit real. Mantener actualizado: después de modificar este módulo, anteponer la entrada nueva bajo la fecha de hoy (o crear el día si no existe).

**Commits registrados:** 109 | **Rango:** 2026-06-02 → 2026-06-23

---


## 2026-07-03

- 🐛 `(pendiente commit)` fix(md_bento_theme): barra sticky "Añadir al carrito" de la PDP (`.md-sticky-atc-bar`) quedaba `position: static` en vez de `fixed` — vivía dentro del bloque `body.md-route-shop #wrap:not(.md-shop) { ... }`, pero `shop_ux.js` la crea con `document.body.appendChild(...)` (fuera de `#wrap`), así que ese ancestro nunca coincidía. Se saca a una regla standalone en `site_unify.scss`, sin depender de `body.md-route-shop` — evita reactivar el resto de ese bloque grande, que choca con las cards bento del grid (ver revert de ayer/hoy en `medicine_depot_portal`).
- ↩️ `(pendiente commit)` revert(md_bento_theme): se quita el ajuste de esquinas de la cintilla de descuento — la cintilla en sí se revirtió en `custom_shop_qty_selector` a pedido explícito, se mantiene solo el pill de la esquina de la imagen.

## 2026-07-02

- ✨ `(pendiente commit)` feat(md_bento_theme): rediseño Bento del carrito (`/shop/cart`) — nuevo `views/cart_templates.xml` + `static/src/scss/md_cart.scss`: enlace placeholder "Guardar para después" junto a "Remove" (`cart_line_save_for_later`), precio de línea en negrita (`cart_line_price_bold`), selector de cantidad en pill redondeado (`.oe_cart .css_quantity`), y tarjeta de resumen (`.o_total_card`) con `border-radius: 12px`, borde `#eaeaea` y fondo dark-mode-aware (override en `md_dark.scss`). La estructura base (grid 7/5, botón w-100, cupón alineado, tabla sin bordes rígidos) ya cumplía el spec nativamente — no requirió cambios.
- 🔄 `(pendiente commit)` refactor(md_bento_theme): activar `md_shop_products_bento` (quitar `active="False"`) — el catálogo estaba sin la clase `.md-shop` desde la migración a Odoo 19, dejando dormido todo el CSS de tarjetas bento (`border-radius`, sombra, fondo dark-mode-aware) ya escrito en `md_shop.scss`. Se sube `border-radius` de 14px a 16px en el bloque de "restauración" de modo claro (card + imagen) para cumplir el spec; el resto de ese bloque (tamaño de botones CTA, posición del badge de stock) se deja intacto a propósito.
- 💄 `(pendiente commit)` feat(md_bento_theme): posicionar el nuevo badge de descuento (`.o_md_discount_badge`, definido en `custom_shop_qty_selector`) en la esquina superior derecha del tile de imagen del producto, opuesta al badge "A la mano" (top-left) — mismo patrón `inset-block-start`/`inset-inline-end` glassmorphism ya usado en `.o_sqty_stock`.

## 2026-07-01

- 🐛 `(pendiente commit)` fix(md_bento_theme): corregir selector de dark mode roto (`.o_dark_mode`/`[data-bs-theme]`, nunca presentes en el frontend) a `body[data-color-scheme="dark"]`/`body:not([data-color-scheme="dark"])` en `md_bento.scss`, `md_dark.scss` (archivo completo), `md_shop.scss` (incl. patrón inverso siempre-verdadero), `md_tokens.scss` y `snippets/_s_socios.scss`. Ver `docs/audits/2026-07-01_backend_dark_mode_audit.md`.

## 2026-06-23

- 🐛 `31894c4` fix(md_bento_theme): eliminar template md_remove_hubspot_tracking que causa ParseError en Odoo 19
- 🐛 `daa5ea4` fix(website): resolver bloqueos cors de iframes, eliminar script obsoleto de hubspot y corregir integracion de recaptcha

## 2026-06-18

- 🔧 `a58de00` chore(pharma_reports): integrar cambios de main en rama test
- ✨ `3e27bfd` feat(md_bento_theme): reemplazar imagen promo banner y optimizar escalado bento
- ✨ `b27b3d5` feat(theme): aplicar bento-glass-card a todas las secciones del website
- 🔧 `e4e33cd` chore(theme): merge test en main — glassmorphism bento footer y clase utilitaria global
- 🔄 `1de1a55` refactor(theme): implementar diseno glassmorphism bento en el footer y crear clase utilitaria global

## 2026-06-17

- ✨ `cc5df67` feat(md_bento_theme): reducir espacios en blanco del homepage
- ✨ `d6dcbc4` feat(md_bento_theme): título socios en mayúsculas con text-transform
- ✨ `80da68a` feat(md_bento_theme): renombrar sección socios como eyebrow "● Socios Comerciales"
- 🐛 `0a18301` fix(md_bento_theme): altura de banner responsiva para pantallas grandes
- ✨ `dea5427` feat(md_bento_theme): srcset responsivo y calidad de imagen del banner
- 🐛 `c885308` fix(md_bento_theme): corregir compilacion SCSS del banner — valores simples
- 🔄 `5fbe129` refactor(md_bento_theme): banner bento-compliant — bordes, shadow, altura responsiva
- ✨ `e462dbd` feat(md_bento_theme): mejoras de diseño bento en homepage
- ✨ `c25822d` feat(md_bento_theme): banner promocional Mundial 2026 y reducir gap hero
- ✨ `81ac609` feat(md_bento_theme): banner promocional Mundial 2026 y reducir gap hero

## 2026-06-14

- 🔧 `3a3d958` chore(md_bento_theme): compactar selector de empresas en systray reemplazando texto por icono

## 2026-06-13

- 🐛 `1cd59a4` fix(md_bento_theme): resolver incompatibilidad de contraste en dropdowns para modo claro y oscuro en v19

## 2026-06-10

- 📚 `678aa01` docs(global): auditoria de modulos, actualizacion de documentacion, propuesta de engine v2 y estructura inicial de manuales visuales para usuarios
- • `789e9cd` improvement(md_bento_theme): restauracion del diseno ui/ux de la tienda online desde el historial de la rama test
- 🐛 `6841666` fix(theme): unify typography, login design, and button styles globally
- • `dfd8b37` improvement(theme): comprehensive typography and sizing audit fixes
- • `437d78e` improvement(theme): optimize heading sizes for desktop and normalize font weights
- • `d4ebbff` improvement(theme): replicate clean typography and enhance carousel design
- 🐛 `128a3e6` fix(website): restauracion funcional del carrusel de marcas e implementacion de diseno liquid glass
- 🐛 `d5afee1` fix(theme): correct typography family and gradient clipping for partners section title
- • `2e07709` improvement(theme): apply liquid glass design and brand colors to partners snippet
- 🐛 `036adc8` fix(theme): remove javascript dependencies and body-class prefix for login style layout
- • `43269bb` improvement(theme): align login background and card style to portal dashboard design
- • `6c7b1a7` improvement(theme): replicate portal background and liquid glass card designs on the bento homepage
- 🐛 `84d96ee` fix(theme): actualizacion de xpath del contenedor de copyright en layout principal para asegurar compatibilidad con odoo 19
- 🐛 `9bfb7a7` fix(theme): remove native odoo copyright footer bar to avoid duplicate footers
- 🐛 `abfe3d4` fix(theme): directly style login card and card-body to ensure liquid glass design and logo show without js class injection
- 🐛 `82b46bd` fix(theme): fix login glass island css selectors, add liquid glass styling, company logo layout, and entrance animations
- • `23aae11` improvement(md_bento_theme): enhance brand logos marquee layout with premium glassmorphism and smooth animations
- • `5a2db9e` improvement(medicine_depot_portal): adapt dashboard cards to liquid glass and unify logos ticker design
- • `a1b2fb4` improvement(medicine_depot_portal): corregir sizing de farmacovigilancia y redireccionar MedicD a url externa
- 🐛 `768ea42` fix(website/footer): rediseño visual del footer con fondo claro, logo corporativo y linea de acento brand gradient
- 🐛 `a773124` fix(website/footer): unificacion de fuente tipografica y ajuste responsivo de sizing en el footer global conforme al diseño del home
- 🐛 `9d4e193` fix(website/footer): unificacion de fuente tipografica y ajuste responsivo de sizing en el footer global conforme al diseño del home
- 🐛 `1e17dfc` fix(ui): unifica navbar y estilos de afiliacion y sucursales
- 🐛 `3ce49f1` fix(theme/scss): correccion de calculos entre rem y porcentajes reemplazandolos por calc() para permitir la compilacion de assets frontend
- ✨ `38d0dac` feat(website/auth): rediseño UX del flujo de login y registro para usuarios nuevos asegurando mayor claridad visual

## 2026-06-09

- 🐛 `c6d900c` fix(md_bento_theme): actualizar carrusel de socios con los 16 laboratorios oficiales

## 2026-06-08

- 🔧 `4618976` chore(md_bento_theme): bump version 19.0.1.0.8 para forzar upgrade en deploy
- ✨ `970a843` feat(md_bento_theme): activar raíz Bento en PDP y refinar UX (auditoría 19)
- 🐛 `44b8c2c` fix(website): unificar navbar de shop e integrar carrito nativo
- 🐛 `3542ec4` fix(website): restaurar cards de productos al estado de main
- 🐛 `5e21c8c` fix(website): remocion de llamada a template qweb inexistente md_nav_cart para restaurar acceso a la tienda
- 🧪 `a7f4fb5` test(website): implementacion de auditoria playwright y restauracion de layout global navbar y shop desde main
- 🐛 `ab47803` fix(medicine_depot_portal): restaurar estilos de botones/cards de main y agregar carrito al navbar Bento
- 🐛 `7e5d2cb` fix(medicine_depot_portal): eliminar navbar duplicado en /shop* y corregir overflow móvil del buscador de tienda
- 🐛 `d4f622e` fix(medicine_depot_portal,md_bento_theme): corrige contraste de badge de stock y regresion de dark mode en mapa de sucursales

## 2026-06-04

- 🔄 `c7e9e05` refactor(shop): limpia XML/SCSS y mejora auditoría Playwright
- ✨ `0e710a7` feat(shop): rediseño bento-box de tienda, transparencia de imágenes nativas y habilitación de carrito

## 2026-06-03

- ✨ `972eef7` feat(website): usar logos oficiales en socios comerciales
- 🐛 `43aeb38` fix(ui): correccion de herencia qweb para evitar solapamiento de navbar y restauracion de estilos nativos en el footer
- 🐛 `72a838b` fix(website): cargar tokens scss como asset compatible con odoo.sh
- ✨ `7a46cb2` feat(website): implementacion de snippet bento para socios comerciales validado via playwright en odoo.sh v19
- 🔄 `b12ee4b` refactor(web): separar capas web medicine depot

## 2026-06-02

- 🐛 `85f7829` fix(shop): excluir o_add_wishlist de regla .btn y forzar dimensiones 44px con alta especificidad
- 🐛 `d56aa48` fix(shop): quitar backdrop-filter del wishlist btn para eliminar franja de gradiente superior
- 🐛 `1fe5c9c` fix(shop): forzar fondo blanco explicito en card para evitar transparencia
- 🐛 `f1ab05d` fix(shop): overflow:visible en card para desbloquear boton Agregar clipado
- 🐛 `4361855` fix(shop): neutralizar order:6 (Bootstrap order-last) del precio y justify-content del sub
- ✨ `3e4ce4d` feat(shop): 15 mejoras de diseno con animaciones en tarjetas bento
- 🐛 `33b345d` fix(shop): remover fondo de rayas diagonales, fondo neutro #F2F7FA
- 🐛 `00931b9` fix(shop): separar combined rule para dar max-content al reveal y subir especificidad del fondo
- 🐛 `52a3294` fix(shop): separar background en propiedades explicitas y usar max-content en reveal para resolver layout
- 🐛 `dea54ac` fix(shop): corregir fondo rayas diagonales y visibilidad del boton Agregar en tarjeta bento
- ✨ `b1b6340` feat(shop): replicar diseno bento con fondo rayas diagonales, badge A la mano coloreado y boton Agregar verde pill con icono carrito
- 🐛 `40348a7` fix(style): refactorizacion de operacion matematica rem/% usando css calc() para evitar error de compilador sass
- 🐛 `54d6893` fix(ui): restaurar cta compacta en tarjetas bento
- 🔄 `6d7ac99` refactor(ui): auditoria automatizada via playwright e implementacion de correcciones estructurales bento-box en vistas publicas
- 🐛 `52fa576` fix(shop): forzar upgrade de vista y compactar CTA a 'Agregar'
- ✨ `997d9a4` feat(shop): rediseño de tarjeta de producto con jerarquia bento y validacion dom automatizada via playwright
- 🐛 `243c223` fix(footer): ocultar tira nativa redundante y dejar panel Bento limpio
- 🐛 `5a6d229` fix(shop): altura compacta real (40px) de controles en md_shop.scss
- 🐛 `c8aab32` fix(footer): fondo neutro literal y texto legible (claro/oscuro)
- 🐛 `a67241d` fix(layout): inyectar md-bento-footer via t-attf-class
- 🔄 `056a357` refactor(ui): implementacion de ui rescue plan para footer, login y tienda alineado a diseño bento-box
- 🐛 `8bfec3e` fix(style): escape de funcion css nativa min() para evitar colapso del compilador sass en assets_frontend
- 🐛 `6959afe` fix(style): escape de funcion css nativa min() para evitar colapso del compilador sass en assets_frontend
- 🔄 `855a187` refactor(shop): limpieza de scss del catalogo, reset de grid bento y optimizacion ergonomica de botones
- 🐛 `6a5565d` fix(shop): ampliar selectores wishlist a cualquier md-product-card independiente del contexto
- 💄 `2cd14b6` style(shop): implementacion de espaciado fluido y alineacion flex en grid de productos para optimizacion de diseño bento
- 🐛 `90c8449` fix(shop): corregir posicion y tamano del boton wishlist en catalogo y pagina de producto
- • `9ead5d9` improvement(shop): espaciado fluido y alineacion flex en grid de productos para optimizacion de diseño bento
- • `ccd20ad` improvement(shop): aplanar footer, precio prominente sobre el CTA y boton agregar como pill comodo
- 🐛 `bb9c3dc` fix(shop): corregir doble separacion banner-header y espacio fantasma de meta en tarjetas
- • `856aedf` improvement(shop): implementacion de espaciado fluido y alineacion flex en grid de productos para optimizacion de diseño bento
- 🔄 `ad5e9b4` refactor(shop): aumentar separacion visual de tarjetas bento del catalogo
- 🐛 `47ab2e0` fix(shop): resolucion de incompatibilidad rem/vw en .md-product-card implementando css calc()
- 💄 `9b2fd7d` style(shop): optimizacion de sizing responsivo para tarjetas bento e implementacion de nuevo fondo en imagenes de producto
- 💄 `4e5e788` style(shop): optimizacion de sizing responsivo para tarjetas bento e implementacion de nuevo fondo en imagenes de producto
- ✨ `9635b34` feat(ecommerce): badge a la mano como overlay sobre la imagen + 5 microinteracciones en tarjetas bento
- ✨ `643cca2` feat(ecommerce): unificar etiqueta a la mano por sucursal (numero + pzs, rojo agotado) y emparejar tarjetas bento
- ✨ `0909ff5` feat(ecommerce): rediseño de tarjeta de tienda estilo referencia con etiqueta a la mano y precio mas grande
- ✨ `6d2dc89` feat(ecommerce): implementacion de etiqueta de inventario a la mano filtrado por sucursal del cliente con diseño bento
- 🔄 `e4249ec` refactor(shop): restaurar grid bento del catalogo en odoo 19
- 🐛 `cbd3cf2` fix(frontend): ejecutar mejoras criticas de auditoria ui ecommerce
- 🔄 `4cb3616` refactor(theme): migracion de selectores xpath @class a hasclass en vistas para cumplir estandar de odoo 19 y limpieza de warnings
- 🐛 `b12240d` fix(frontend): implementacion de calc() css para evitar incompatibilidad rem/vw en compilador sass y fix de asset 404 en server_management
- 🐛 `44ba555` fix(theme): actualizacion de xpath de imagenes de producto a la nueva arquitectura de website_sale en odoo 19 validado por documentacion
- 🐛 `e21985d` fix(theme): actualizacion de xpath oe_product_cart a la nueva estructura de products_item en odoo 19
- 🐛 `12d7180` fix(theme): migracion de xpath products_grid_before a la nueva estructura de website_sale en odoo 19 para permitir instalacion del tema
- 🐛 `0a5478a` fix(theme): actualizacion de xpath de top_menu para compatibilidad con la estructura del navbar en odoo 19
- ✨ `fa5331a` feat(md_bento_theme): add bento ecommerce theme
