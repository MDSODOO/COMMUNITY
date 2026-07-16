# Changelog — medicine_depot_portal

Historial generado automáticamente a partir de `git log -- medicine_depot_portal`. No es prosa editorial: cada línea es un commit real. Mantener actualizado: después de modificar este módulo, anteponer la entrada nueva bajo la fecha de hoy (o crear el día si no existe).

**Commits registrados:** 237 | **Rango:** 2026-05-09 → 2026-06-29

---


## 2026-07-03

- ↩️ `(pendiente commit)` revert(medicine_depot_portal): se revierte el fix de `public_surface_bridge.js` de este mismo día — al corregir la asignación de `body.md-route-shop`, activó de golpe una docena de reglas en `site_unify.scss` que dependían de esa clase y llevaban tiempo (posiblemente siempre) dormidas, varias de las cuales chocan con el estilo de las cards bento del grid (`md_shop.scss`), rompiendo texto/tamaño/estilo visualmente. El riesgo de tocar la página principal de la tienda supera el beneficio de arreglar la barra sticky de "Añadir al carrito" en la PDP — queda pendiente como tarea separada (requiere auditar y armonizar las reglas de `site_unify.scss` contra `md_shop.scss` antes de reactivar `md-route-shop`).
- 🐛 `(pendiente commit)` fix(medicine_depot_portal): `public_surface_bridge.js` nunca asignaba las clases `md-route-*`/`md-site-unified`/`md-wrap-unified` al body — usaba `document.addEventListener('DOMContentLoaded', ...)`, pero al ser un `@odoo-module` (script type="module", carga tipo "defer"), `DOMContentLoaded` casi siempre ya había disparado antes de que el listener se registrara, así que nunca corría. Detectado en vivo: la barra sticky "Añadir al carrito" de la PDP (`.md-sticky-atc-bar`, gateada por `body.md-route-shop` en `site_unify.scss`) quedaba `position: static`, apareciendo pegada al fondo de la página en vez de flotar sobre el viewport. Fix: ejecutar la inicialización inmediatamente si `document.readyState` ya no es `'loading'`. Afecta a TODAS las rutas (`md-route-shop`, `md-route-blog`, `md-route-portal`, etc.), no solo el carrito — bug preexistente, no introducido hoy.

## 2026-07-01

- 🐛 `(pendiente commit)` fix(medicine_depot_portal): corregir contraste de .btn-primary/.btn-secondary y flechas de statusbar en dark mode (backend_dark.scss)
- 🐛 `(pendiente commit)` fix(medicine_depot_portal): mover overrides muertos de `backend_bento.scss`/`backend_tokens.scss` a `backend_dark.scss` (gateados por `.o_dark_mode`/`[data-bs-theme]`, nunca coincidían con el DOM real); corregir selectores frontend rotos en `login_custom.scss`, `portal_bento.scss` y `snippets/_s_branches.scss` a `data-color-scheme`/`prefers-color-scheme`, los selectores reales del toggle del sitio público. Ver `docs/audits/2026-07-01_backend_dark_mode_audit.md`.
- 🐛 `acce4b7` fix(medicine_depot_portal): menú de Acción (⚙) de las vistas Form pintaba blanco en dark mode pese a computed style correcto — bug de compositing por `backdrop-filter` + fondo casi-opaco (0.94) en popover `position:fixed`. `--md-dropdown-bg` a 1.0 de opacidad y se quita el `backdrop-filter` de dropdowns. Verificado en navegador real (Contactos).

## 2026-06-29

- 🔧 `af60e60` chore(repo): limpieza jerárquica y reorganización de archivos raíz
- ✨ `eedfcb8` feat(medicine_depot_portal): botón de sesión dinámico en navbar

## 2026-06-23

- 🐛 `daa5ea4` fix(website): resolver bloqueos cors de iframes, eliminar script obsoleto de hubspot y corregir integracion de recaptcha

## 2026-06-19

- 🔄 `4bcab86` refactor(server_management_ogum): resolver warnings de odoo 19 incluyendo descripciones, seguridad, tipos booleanos y widgets mal ubicados

## 2026-06-18

- 🔄 `1de1a55` refactor(theme): implementar diseno glassmorphism bento en el footer y crear clase utilitaria global

## 2026-06-17

- 🐛 `1fccf59` fix(frontend): refactorizar inicializacion del mapa en un public widget seguro para evitar crash (Cannot read properties of null reading body) en el website builder
- 🐛 `ac7e748` fix(frontend): aplicar dark mode al mapa OSM mediante filtros CSS y establecer fondo oscuro de fallback para adblockers
- 🔄 `e170ee0` refactor(branches): panel bento apilado debajo del mapa, mismo ancho (full-width)
- 🐛 `63b50be` fix(branches): mapa min-height 520px + panel stretch + umbral test 500px
- ✨ `6aec1f4` feat(branches): mapa más grande + sección QR dedicada debajo del mapa
- 🔄 `a563ddf` refactor(frontend): reemplazar API de QRs de terceros por controlador nativo de odoo para evitar bloqueos por adblockers (ERR_BLOCKED_BY_CLIENT)

## 2026-06-13

- 🐛 `aa649e4` fix(medicine_depot_portal): registrar backend_dark.scss en web.assets_web_dark para dark mode real de Odoo 19
- 🐛 `0e1dbd1` fix(medicine_depot_portal): corregir selector de dark mode para dropdowns del backend en v19
- 🐛 `a71aad8` fix(medicine_depot_portal): resolver incompatibilidad de contraste en dropdowns para modo claro y oscuro en v19

## 2026-06-11

- 🐛 `3040326` fix(medicine_depot_website): corregir render de inventario y cantidad en ecommerce

## 2026-06-10

- ✨ `f84f022` feat(medicine_depot_website): mostrar carrusel de productos relacionados cuando no hay inventario a la mano
- • `e520a16` improvement(medicine_depot_portal): extender Liquid Glass a tiles públicos y refinamiento de navbar
- 🐛 `8d31884` fix(frontend/tours): revertir path DOMPurify inexistente en Odoo 19
- 🐛 `cdcf7a9` fix(frontend/tours): actualización de API de tours, inclusión de DOMPurify y restauración de dependencias de Owl assets
- 📚 `678aa01` docs(global): auditoria de modulos, actualizacion de documentacion, propuesta de engine v2 y estructura inicial de manuales visuales para usuarios
- • `d36437b` improvement(login): rediseño de layout y card para eliminar espacio muerto
- 🐛 `242c104` fix(portal): eliminar linea blanca entre login y footer aplicando gradiente a wrapwrap
- • `3f13111` improvement(portal): alinear fondo de login con gradiente de pagina restringida
- 🐛 `2e16ac2` fix(portal): eliminacion de xpath obsoleto no_footer para resolver parse error en odoo 19
- 🐛 `60c5455` fix(portal): correccion de xpath para garantizar footer en odoo 19
- ✨ `83dd050` feat(portal): unificacion liquid glass en mi portal y footer global garantizado
- • `7dd8891` improvement(medicine_depot_portal): rediseno visual de landing page restringida del shop
- 🐛 `6841666` fix(theme): unify typography, login design, and button styles globally
- • `dfd8b37` improvement(theme): comprehensive typography and sizing audit fixes
- • `437d78e` improvement(theme): optimize heading sizes for desktop and normalize font weights
- 🐛 `036adc8` fix(theme): remove javascript dependencies and body-class prefix for login style layout
- • `f905f9d` improvement(portal): apply portal background and card styling on restricted shop page
- • `118bfac` improvement(portal): replicate portal dashboard background and liquid glass card tones on home page
- • `2b140e6` improvement(portal): apply liquid glass design to home sections and cards for aesthetic consistency
- 🐛 `f2a27d9` fix(portal): remove display block override for header#top in login/signup to ensure it is hidden
- 🐛 `d0b35b3` fix(portal): unify bento navbar on login/signup and resolve duplicate login buttons
- • `addd630` improvement(medicine_depot_portal): style all security components and fix layout background specificity
- • `b527808` improvement(medicine_depot_portal): apply ambient gradient background to all portal pages globally
- 🐛 `84623d9` fix(portal): actualizacion de xpath en la vista de seguridad del portal para compatibilidad con odoo 19
- • `a8b3767` improvement(medicine_depot_portal): adapt account security change password form to bento layout
- • `5a2db9e` improvement(medicine_depot_portal): adapt dashboard cards to liquid glass and unify logos ticker design
- 🐛 `49c160c` fix(medicine_depot_portal): auditoria de seguridad, inyeccion de tokens csrf, sanitizacion de controladores publicos y validacion de pruebas automatizadas
- • `1480069` improvement(medicine_depot_portal): corregir colision de estilos en campos de farmacovigilancia
- ✨ `6f11da5` feat(website): refactorizacion de form farmacovigilancia y creacion de landing page animada para acceso restringido a la tienda
- • `a1b2fb4` improvement(medicine_depot_portal): corregir sizing de farmacovigilancia y redireccionar MedicD a url externa
- • `cb27479` improvement(medicine_depot_portal): replicar diseno de dos columnas con aside y checklist en farmacovigilancia
- • `5eb8b83` improvement(medicine_depot_portal): unificacion visual de portal, enlaces de footer y titulos
- • `47b2666` improvement(medicine_depot_portal): optimizar contraste de colores y compresion del footer
- • `d2d03a1` improvement(medicine_depot_portal): unificacion visual de farmacovigilancia con afiliacion y sucursales
- 🐛 `768ea42` fix(website/footer): rediseño visual del footer con fondo claro, logo corporativo y linea de acento brand gradient
- 🐛 `a773124` fix(website/footer): unificacion de fuente tipografica y ajuste responsivo de sizing en el footer global conforme al diseño del home
- 🐛 `9d4e193` fix(website/footer): unificacion de fuente tipografica y ajuste responsivo de sizing en el footer global conforme al diseño del home
- 🐛 `3122d71` fix(website): unifica sizing tipografico con home en secciones publicas
- 🐛 `2a55ce8` fix(theme): unificacion de la tipografia global basada en el home y validacion mediante playwright
- 🐛 `1e17dfc` fix(ui): unifica navbar y estilos de afiliacion y sucursales
- 🐛 `3ce49f1` fix(theme/scss): correccion de calculos entre rem y porcentajes reemplazandolos por calc() para permitir la compilacion de assets frontend
- 🐛 `136a9b9` fix(auth): actualizacion de xpath del formulario de login para recuperar compatibilidad con dom de odoo 19
- ✨ `38d0dac` feat(website/auth): rediseño UX del flujo de login y registro para usuarios nuevos asegurando mayor claridad visual
- ✨ `9840422` feat(medicine_depot_portal): rediseno liquid glass en afiliacion y sucursales alineado al portal de usuarios
- 🐛 `a146605` fix(website): homologacion de paleta de colores en secciones afiliacion y sucursales usando variables scss globales de la marca

## 2026-06-09

- 🐛 `c64f9ee` fix(website): reemplazo de wordmarks generados por logos oficiales de bruluagsa, bruluart, amsa y serral
- ✨ `f935a49` feat(website): actualizacion de logos de laboratorios medicos y rediseno de carrusel estilo tarjetas corporativas
- ✨ `151e277` feat(website): implementacion de diseno ui desde mockups para la seccion afiliacion y sucursales usando bootstrap 5 y scss

## 2026-06-08

- 🔄 `51db37e` refactor(website): rediseñar /sucursales con layout Bento responsivo
- 🐛 `7e494f1` fix(website): unificar diseno pill del navbar en todas las rutas
- 🐛 `be5477a` fix(website): eliminar navbar bento duplicado en paginas public_shell
- 🐛 `7c9ee6f` fix(website): corregir padding-top del navbar flotante para unificar altura en todas las rutas
- 🐛 `73e9bc3` fix(website): unificacion global de navbar y optimizacion responsiva del grid bento y mapa en vista de sucursales
- 🐛 `44b8c2c` fix(website): unificar navbar de shop e integrar carrito nativo
- 🧪 `a7f4fb5` test(website): implementacion de auditoria playwright y restauracion de layout global navbar y shop desde main
- 🐛 `ab47803` fix(medicine_depot_portal): restaurar estilos de botones/cards de main y agregar carrito al navbar Bento
- 🐛 `7e5d2cb` fix(medicine_depot_portal): eliminar navbar duplicado en /shop* y corregir overflow móvil del buscador de tienda
- 🐛 `d4f622e` fix(medicine_depot_portal,md_bento_theme): corrige contraste de badge de stock y regresion de dark mode en mapa de sucursales
- 🔧 `56e5638` chore(medicine_depot_portal): implementacion de auditoria playwright y restauracion de navbar desde main

## 2026-06-03

- 🐛 `43aeb38` fix(ui): correccion de herencia qweb para evitar solapamiento de navbar y restauracion de estilos nativos en el footer
- 🔄 `b12ee4b` refactor(web): separar capas web medicine depot

## 2026-06-02

- 🔄 `056a357` refactor(ui): implementacion de ui rescue plan para footer, login y tienda alineado a diseño bento-box
- 💄 `9b2fd7d` style(shop): optimizacion de sizing responsivo para tarjetas bento e implementacion de nuevo fondo en imagenes de producto
- 🐛 `bc187d7` fix(pos): normalizar etiquetas visibles a A la mano
- 🔄 `04ead28` refactor(theme): adaptar bento y formularios a modo oscuro
- 🐛 `7a7c5e1` fix(theme): terminologia de inventario y dark mode en tiles bento de pagina de inicio
- 🔄 `c29ace2` refactor(theme): condicionar fondo oscuro del mapa de sucursales a dark mode via html:not(.o_dark_mode)
- 🔄 `301d12c` refactor(theme): tarjetas bento con variables bs5 y atenuacion de sombras en dark mode
- 🔄 `c8cb67b` refactor(theme): variables nativas BS5 en formularios de login y afiliacion para soporte dark mode
- 🐛 `cbd3cf2` fix(frontend): ejecutar mejoras criticas de auditoria ui ecommerce
- 🐛 `b12240d` fix(frontend): implementacion de calc() css para evitar incompatibilidad rem/vw en compilador sass y fix de asset 404 en server_management
- 🔄 `bba4059` refactor(backend): restauracion de light mode como tema base y encapsulacion de reglas oscuras en o_dark_mode

## 2026-06-01

- 🐛 `3184106` fix(ui): dark mode tokens and backend contrast hardening
- 🔄 `26deeee` refactor(backend): refactorizacion de scss implementando css variables dinamicas para soporte nativo de light/dark mode
- 🐛 `ed56709` fix(ui): resolucion de error de compilacion SASS por unidades incompatibles vw y px en bundle de impresion
- • `d966ea1` improvement(backend): sistema de design tokens y refactor UI Bento-box (29 mejoras)
- 🔄 `6b78ad4` refactor(core): actualizacion de sql_constraints a estandar odoo 19 y limpieza de modelos huerfanos detectados en logs
- ✨ `ca7ce78` feat(backend-ui): densidad y glass en hoja/statusbar/chatter con vars nativas reales de Odoo 19
- ✨ `899bad2` feat(ui): ejecucion del plan de 69 mejoras UI/UX (login, sucursales, tienda, portal)

## 2026-05-29

- 🔄 `83bc92d` refactor(portal): reemplazar estilos inline por tokens SCSS y clases Bootstrap
- 🐛 `f350dd5` fix(portal): inyeccion de address_type y selectores de formulario para resolver TypeError en el JS del portal
- 🐛 `9cfdc1a` fix(portal): auditoria de qweb y restauracion de diseno bento/glassmorphism en la pantalla de login
- 🐛 `518f725` fix(portal): resolucion de KeyError cambiando variable partner por request.env.user.partner_id en formulario my account
- 💄 `3769c62` style(website): eliminacion de boton DM modo y desactivacion de navbar nativo en tienda y dashboard de usuario
- 🐛 `7f91b58` fix(portal): correccion de xpath en portal_templates para resolver ParseError y ajustar a la nueva estructura del DOM
- 💄 `3f3a63f` style(portal): rediseno de vista my/account implementando layout bento-box y reorganizacion de campos custom de studio
- ✨ `779b5d2` feat(website): adicion de boton en navbar exclusivo para usuarios logueados y redireccion a dashboard estilo bento

## 2026-05-28

- 🐛 `5994ea3` fix(portal): restringir acceso al modelo de farmacovigilancia a administradores (base.group_system)
- 🐛 `20bb608` fix(portal): restringir el menu de farmacovigilancia a administradores (base.group_system)
- 🐛 `432132d` fix(medicine_depot_portal): fix selection value for x_studio_contact_type during affiliation
- ✨ `4098038` feat(medicine_depot_portal): completar fases 2.2-2.6 y fase 3 del plan Bento

## 2026-05-27

- • `bdb26e8` improvement(medicine_depot_website): unify SCSS assets and implement Homepage Bento & Glassmorphism redesign
- • `51bb9bd` improvement(medicine_depot_portal): add SEO metadata and Open Graph fallbacks for production readiness
- 🐛 `81c6ad0` fix(spacing): revertir mb-4 en section-heads y corregir selectores UX
- • `78938ba` improvement(xml): mejorar distribución espacial de bloques home y tienda
- • `c60dc39` improvement(medicine_depot_portal): fix navbar text sizes, colors and remove blog
- ✨ `f21a29f` feat(medicine_depot_portal): mejoras 9,16-20,24-29 + hotfix SCSS min/calc
- 🐛 `5711548` fix(medicine_depot_portal): restore missing @media query in site_unify.scss
- • `f66e62a` improvement(medicine_depot_portal): apply Codex SCSS tweaks for Bento UI
- • `d184386` improvement(medicine_depot_portal): redesign Bento UI Phase 1
- ✨ `8deb77e` feat(medicine_depot_website): redesign public UI surfaces
- ✨ `4df5f00` feat(medicine_depot_portal): redisenar sucursales con mapa hero
- ✨ `4cbf670` feat(medicine_depot_portal): agregar fallback leaflet para sucursales
- ✨ `5cc0c8f` feat(medicine_depot_portal): mejorar mapa responsivo de sucursales
- 🐛 `add7e80` fix(medicine_depot_portal): unificar navbar en tienda
- 🐛 `fbebde9` fix(medicine_depot_portal): usar imports SCSS absolutos para snippets
- 🐛 `7dcf519` fix(s_md_logos_ticker): remove onerror JS inline attributes — XML hotfix
- 🐛 `4ecb45e` fix(medicine_depot_portal): corregir onerror invalido en logos ticker
- 🐛 `7549243` fix(medicine_depot_portal): aplicar hardening fase 11 y smoke tests
- 🔄 `f7d7299` refactor(scss): eliminate duplicate CSS — migrate legacy blocks to modular files
- ✨ `b3415f2` feat(medicine_depot_portal): implementation phase 1 — 8 categories, 52/64 tasks
- 🐛 `1dccc57` fix(medicine_depot_portal): stabilize navbar logo xpath and prevent dual header
- 🐛 `030d229` fix(medicine_depot_portal): make navbar logo xpath robust in odoo19
- • `5bdc5e5` improvement(medicine_depot_portal): complete logo content and branches bento phases
- 🐛 `373ed70` fix(medicine_depot_portal): use str labels in pharmacovigilance selections
- 🐛 `f1243bc` fix(medicine_depot_portal): fallback when blog model is unavailable
- 🐛 `267fd87` fix(core): reubicacion de variables de traduccion en portal controller, fix de dependencias en medicine_depot_portal y asignacion de _name en modelo de picking
- 🐛 `81d548f` fix(i18n): revert es_MX.po to original — remove all manually-written entries
- 🐛 `3fcd731` fix(i18n): corregir referencia de ocurrencia inválida en es_MX.po
- ✨ `41cf3fc` feat(website): apply full 10-phase improvement plan (security, bugs, refactor, i18n, perf, scss, frontend, tests)
- 🐛 `28a831c` fix(branches): preserve svg pin anchors by removing transform override
- 🐛 `0ffda92` fix(nav): add legacy portal route aliases for picking and documents
- ✨ `87ede7e` feat(ui): complete phased bento overhaul for nav, shop, and branches

## 2026-05-26

- ✨ `8dd6696` feat(ui): complete bento polish pass across website and portal
- 🐛 `fdc9375` fix(ui): stabilize branches rendering and harden SCSS for odoo.sh
- 🐛 `73306a0` fix(branches+pdp): strip MDS prefix for state_key lookup + broaden qty stepper selector
- 🐛 `df6209e` fix(gmap): read google.maps.map_id from ir.config_parameter instead of hardcoded DEMO_MAP_ID
- ✨ `157b988` feat(sprint): 4-phase frontend overhaul — promise fix, e-commerce, sucursales, Google Maps
- 🐛 `be8aebb` fix(portal): remove website.http_error inherit — template moved to http_routing in Odoo 19
- ✨ `30b9db9` feat(ui): 29-point visual overhaul — e-commerce, hero, nav, blog, service grid
- ✨ `12c7a5f` feat(portal): unifica rutas de contacto, añade barra de progreso en wizard y corrige layout de hero
- 🐛 `5571974` fix(scss): wrap min()/max() with unquote() — libsass evaluates them
- 🐛 `f228ef3` fix(scss): wrap clamp() with unquote() for libsass compatibility
- ✨ `40209d4` feat(website): align design with identity manual
- ✨ `cc72ac9` feat(website): polish public bento design
- ✨ `d98a781` feat(website): fase 1-3 — hotfix navbar, mejoras UI Bento, mapa ADN Yucatán
- ✨ `0370922` feat(medicine_depot_website): refine public site design
- 🐛 `f886fc5` fix(medicine_depot_portal): normalize branch selection value
- 🔄 `a9f55bd` refactor(medicine_depot_portal): footer + container unificados con tokens SCSS
- ✨ `9e35b8a` feat(medicine_depot_portal): container base + escala cromática de secciones
- 🔄 `439dd2f` refactor(medicine_depot_portal): fases 2-5 UI — purga CSS muerto, tokens, hamburger, max-width h2
- 🐛 `7113d12` fix(medicine_depot_portal): fase 1 UI — eliminar uppercase cascade + footer corporativo oscuro
- 🔄 `4fbed05` refactor(medicine_depot_portal): unify bento scss tokens
- 🐛 `bd108c7` fix(medicine_depot_portal): escape css min in bento shell
- ✨ `03697e7` feat(medicine_depot_portal): unify public bento shell phase 1

## 2026-05-25

- 🐛 `4ec06ce` fix(portal): remove forbidden scss imports and unit mix
- 🐛 `4b3b659` fix(website): replace obj eval with field search
- 🐛 `e3cf48e` fix(i18n): defer controller translations with LazyTranslate
- ✨ `6aa6231` feat(website): migrate portal to Bento and native pages
- 🐛 `13ebc6e` fix(odoo19): replace tree view with list
- ✨ `9ea167a` feat(website): add Bento public shell and pharmacovigilance

## 2026-05-22

- 🐛 `7d623a9` fix(portal): forzar tipo de contacto cliente como campo oculto en afiliacion
- ✨ `2a99bc8` feat(portal): endurecer flujo de afiliacion con validacion backend y errores de UI
- 🐛 `8ef2064` fix(portal): poblar sucursal de afiliacion con stock.warehouse y adaptar guardado por tipo de campo
- ✨ `1fc03ff` feat(portal): estandarizacion de registros de afiliacion forzando nombres en mayusculas, idioma es_MX y rango de cliente

## 2026-05-19

- 🐛 `4d142c6` fix(portal): robustecer xpath de portal_my_details para evitar ParseError sin perder personalizacion
- ✨ `10d1c43` feat(portal): integracion de carga multipart de expediente medico en my/account y sistema de alertas para perfiles incompletos

## 2026-05-18

- 🐛 `8ffde28` fix(portal): ajustar paleta bento y contraste en afiliacion para visibilidad del header y secciones
- 🐛 `1cb1d3a` fix(portal): restauracion del navbar nativo en afiliacion y correccion de contenedores para eliminar zonas en blanco del layout
- ✨ `ef44f7a` feat(portal): diseno focus sin navbar en afiliacion, logica condicional de ocultamiento y banners de notificacion de documentos faltantes en my/home
- 🔄 `a02b303` refactor(portal): integrar afiliacion en card unico y agregar prueba multipart de subida de archivos
- 🐛 `fd7e8f5` fix(portal): reemplazo de campo inexistente job_position por function en afiliacion_templates para resolver error 500 de qweb
- ✨ `ffee4b3` feat(portal): homologacion bento en afiliacion, soporte multipart/form-data e integracion de 10 campos de odoo studio incluyendo documentos cofepris
- 🐛 `cedce98` fix(fase-1): eliminar CDN externa y homologar terminología "A la mano" en vistas de admin
- 🐛 `c8d5cee` fix(medicine_depot_portal): inyectar decoys data-placeholder_count y robustecer patch JS
- 🔧 `1eed805` chore(medicine_depot_portal): retirar login_templates.xml vacio del manifest
- 🐛 `f4b392c` fix(medicine_depot_portal): patch defensivo de PortalHomeCounters para evitar TypeError en /my/home
- 🐛 `487db45` fix(medicine_depot_portal): restaurar o_portal_docs_counter en layout bento
- 🐛 `c89b6f6` fix(core): eliminar wrapper t-name redundante en afiliacion_page y validar ACL x_sale_order_line
- 🐛 `9492ed9` fix(medicine_depot_portal): reemplazar position replace destructivo por atributos
- 🐛 `8c12d64` fix(medicine_depot_portal): reemplazar @import url() de Google Fonts por link en template
- 🐛 `2e191a5` fix(frontend): eliminacion de directiva @import prohibida en scss y declaracion estandarizada en manifest para regenerar assets_frontend

## 2026-05-14

- 🐛 `036b1e1` fix(portal): deep search para restaurar span o_portal_docs_counter en my/home y resolver caida del JS nativo
- 🐛 `0ea4eac` fix(portal): restauracion de elementos DOM de contadores en my/home para prevenir TypeError en portal JS
- • `3e49528` improvement(portal): tokens scss compartidos y alineacion de diseno entre portal bento, afiliacion y login
- ✨ `b54652e` feat(portal): guardar contacto y documentos de afiliacion en res.partner al enviar formulario
- 🐛 `2e4e19f` fix(portal): eliminacion de inherit_id en template de afiliacion para resolver ParseError y configuracion de vista primaria con div wrap
- 🐛 `3f23905` fix(portal): aislamiento de template afiliacion en su ruta especifica, restauracion de home/login y correccion estructural de div wrap para prevenir JS TypeError
- ✨ `42e7b8d` feat(medicine_depot_portal): refinamiento de diseño afiliación y pruebas unitarias
- 🐛 `bcb8957` fix(medicine_depot_portal): correccion de XMLSyntaxError limpiando entidades HTML en afiliacion_templates.xml
- ✨ `e146d78` feat(medicine_depot_portal): rediseño página de afiliación con Floating Minimal Card

## 2026-05-12

- 🐛 `bc78960` fix(ui): inyeccion global de nodos fantasma para inicializacion segura de tema colibri
- 🐛 `b71f5d6` fix(portal): inyeccion de nodo fantasma para wishlist y resolucion de crash owl
- 🐛 `3fb41c5` fix(portal): actualizacion de read_group a _read_group para odoo 19
- 🐛 `c0e2657` fix(portal): inyeccion de nodos fantasma para estabilizar JS de tema colibri
- 🐛 `f63d86d` fix(portal): js crash fix, centered cards and bento pdp redesign

## 2026-05-11

- 🔄 `548e33c` refactor(portal): estabilización de XML, UI Bento y fix de JS
- 🐛 `6c34aa9` fix(medicine_depot_portal): stop DOM mutation in login, serve logo via CSS
- • `1fca2d7` improvement(medicine_depot_portal): tint login glass island
- • `5ef5969` improvement(medicine_depot_portal): simplify login glass design
- • `f62207b` improvement(medicine_depot_portal): refine login glass island
- • `6646a49` improvement(medicine_depot_portal): add login glass island
- ✨ `0112252` feat(medicine_depot_portal): glassmorphism login with floating orbs
- • `504d2da` improvement(medicine_depot_portal): center glass login card
- 🐛 `edfbc39` fix(medicine_depot_portal): wrap mixed-unit min() in unquote()
- 🐛 `3437b66` fix(medicine_depot_portal): drop invalid <data/> arch, clean orphan SCSS
- 🐛 `8d4c936` fix(medicine_depot_portal): remove login layout xpaths
- 🐛 `5caadea` fix(medicine_depot_portal): anchor login layout on database card
- 🐛 `e13a6c5` fix(medicine_depot_portal): drop body_classname xpath, anchor login on container
- ✨ `cc561d3` feat(medicine_depot_portal): redesign login page

## 2026-05-10

- ✨ `dfcd400` feat(medicine_depot_portal): highlight pickings bento card
- ✨ `fd5068a` feat(medicine_depot_portal): add native portal bento cards
- 🐛 `d78578a` fix(medicine_depot_portal): brand gradient on navbar and account card
- 🐛 `5d4610e` fix(medicine_depot_portal): silent colibri suppression and stronger mobile breakpoints
- 🐛 `88330f2` fix(medicine_depot_portal): swap orders/quotes slot and clean favorites list
- ✨ `822a81f` feat(medicine_depot_portal): reorder bento cards and improve mobile responsiveness
- 🐛 `9840829` fix(medicine_depot_portal): force white bento cards

## 2026-05-09

- 🐛 `b32a545` fix(medicine_depot_portal): polish portal navbar and cards
- 🐛 `d34af91` fix(medicine_depot_portal): avoid mixed-unit scss min
- 🐛 `341d1a7` fix(medicine_depot_portal): remove portal sidebar and restore bento hover
- 🐛 `3dadfd8` fix(medicine_depot_portal): elimina sidebar residual y refuerza hover/grid
- ✨ `97c5be5` feat(medicine_depot_portal): floating pill navbar + data cards y fix mobile
- ✨ `66b8c04` feat(medicine_depot_portal): integra panel de usuario en header y rebalancea Bento
- 🐛 `7869683` fix(medicine_depot_portal): suprime Uncaught Promise de Colibri y rebalancea Bento a 3 columnas
- 🐛 `5c3f501` fix(medicine_depot_portal): silencia Colibri y refactoriza Bento
- 🐛 `125adf8` fix(medicine_depot_portal): convive con o_portal_docs en lugar de reemplazarlo
- 🐛 `9fe14fc` fix(medicine_depot_portal): preserva ancla o_portal_docs para herencia del core
- 🐛 `6348a4d` fix(medicine_depot_portal): XPath robusto al div o_portal_my_home
- 🐛 `a48e4e3` fix(medicine_depot_portal): xpath via t-call (independiente de version)
- 🐛 `3a6ac73` fix(medicine_depot_portal): xpath robusto via id='wrap' (Odoo 19)
- 🐛 `5f62b77` fix(medicine_depot_portal): corrige XPath para Odoo 19 portal_my_home
- ✨ `8621eff` feat(medicine_depot_portal): Bento-box redesign of /my customer portal
