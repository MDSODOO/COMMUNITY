# Changelog — medicine_depot_website

Historial generado automáticamente a partir de `git log -- medicine_depot_website`. No es prosa editorial: cada línea es un commit real. Mantener actualizado: después de modificar este módulo, anteponer la entrada nueva bajo la fecha de hoy (o crear el día si no existe).

**Commits registrados:** 46 | **Rango:** 2026-05-26 → 2026-06-27

---


## 2026-07-01

- 🐛 `(pendiente commit)` fix(medicine_depot_website): corregir selector de dark mode roto (`.o_dark_mode`/`[data-bs-theme]`, nunca presentes en el frontend) a `body[data-color-scheme="dark"]` (el toggle real del sitio público) en 3 bloques de `medicine_depot_website.scss` (PDP, tarjetas de producto similar). Ver `docs/audits/2026-07-01_backend_dark_mode_audit.md`.

## 2026-06-27

- 🐛 `823e937` fix(website-stock): aplicar filtro de sucursal en SSR y suma de lotes en similares

## 2026-06-18

- ✨ `b27b3d5` feat(theme): aplicar bento-glass-card a todas las secciones del website

## 2026-06-17

- ✨ `6798fce` feat(website): reemplazar banner Hot Sale por promocion Futbol 2026 — pantalla 50 pulgadas (11 jun - 19 jul 2026)
- 🐛 `056b0ce` fix(ecommerce): reemplazar complete_name por display_name en categoria publica para evitar crash en el renderizado del producto

## 2026-06-16

- 🐛 `9e35c92` fix(medicine_depot_website): usar complete_name en categorías de producto para consistencia

## 2026-06-11

- ✨ `a8697d0` feat(medicine_depot_website): pill de categoría con link al shop en header de similares
- 🔄 `a765bd9` refactor(medicine_depot_website): mejorar carrusel de similares con diseño Bento y datos de disponibilidad
- ✨ `2877f5a` feat(medicine_depot_website): carrusel marquee de productos similares por categoría en PDP sin stock
- 🐛 `a0ea88a` fix(medicine_depot_website): actualizar inherit_id de productos alternativos para Odoo 19
- ✨ `d03ec1f` feat(medicine_depot_website): mostrar carrusel de productos relacionados cuando no hay inventario a la mano
- 🐛 `7b4fd09` fix(medicine_depot_website): corregir ruteo y renderizado de filtros de categorías y atributos en el shop

## 2026-06-10

- ✨ `f84f022` feat(medicine_depot_website): mostrar carrusel de productos relacionados cuando no hay inventario a la mano
- 🐛 `0c7cdcc` fix(medicine_depot_website): ocultar controles nativos superpuestos en selector de cantidad
- 🐛 `0481957` fix(medicine_depot_website): actualizar xpath de contenedor de variantes para compatibilidad Odoo 19
- 🐛 `0302246` fix(medicine_depot_website): corregir xpath de variantes de producto para Odoo 19
- • `24ff3b9` improvement(medicine_depot_website): rediseño y mejora UI/UX en template de producto e-commerce
- 📚 `678aa01` docs(global): auditoria de modulos, actualizacion de documentacion, propuesta de engine v2 y estructura inicial de manuales visuales para usuarios

## 2026-06-02

- 🔄 `04ead28` refactor(theme): adaptar bento y formularios a modo oscuro
- 🔄 `c8cb67b` refactor(theme): variables nativas BS5 en formularios de login y afiliacion para soporte dark mode
- 🐛 `cbd3cf2` fix(frontend): ejecutar mejoras criticas de auditoria ui ecommerce
- 🐛 `b12240d` fix(frontend): implementacion de calc() css para evitar incompatibilidad rem/vw en compilador sass y fix de asset 404 en server_management

## 2026-06-01

- ✨ `899bad2` feat(ui): ejecucion del plan de 69 mejoras UI/UX (login, sucursales, tienda, portal)

## 2026-05-27

- • `bdb26e8` improvement(medicine_depot_website): unify SCSS assets and implement Homepage Bento & Glassmorphism redesign
- 🐛 `81c6ad0` fix(spacing): revertir mb-4 en section-heads y corregir selectores UX
- • `78938ba` improvement(xml): mejorar distribución espacial de bloques home y tienda
- ✨ `8deb77e` feat(medicine_depot_website): redesign public UI surfaces
- ✨ `4df5f00` feat(medicine_depot_portal): redisenar sucursales con mapa hero
- • `5bdc5e5` improvement(medicine_depot_portal): complete logo content and branches bento phases
- ✨ `41cf3fc` feat(website): apply full 10-phase improvement plan (security, bugs, refactor, i18n, perf, scss, frontend, tests)
- ✨ `87ede7e` feat(ui): complete phased bento overhaul for nav, shop, and branches

## 2026-05-26

- ✨ `8dd6696` feat(ui): complete bento polish pass across website and portal
- 🐛 `fdc9375` fix(ui): stabilize branches rendering and harden SCSS for odoo.sh
- ✨ `157b988` feat(sprint): 4-phase frontend overhaul — promise fix, e-commerce, sucursales, Google Maps
- ✨ `30b9db9` feat(ui): 29-point visual overhaul — e-commerce, hero, nav, blog, service grid
- 🐛 `de1e084` fix(website): escape hero width min/calc for sass build
- ✨ `12c7a5f` feat(portal): unifica rutas de contacto, añade barra de progreso en wizard y corrige layout de hero
- 🐛 `5571974` fix(scss): wrap min()/max() with unquote() — libsass evaluates them
- 🐛 `f228ef3` fix(scss): wrap clamp() with unquote() for libsass compatibility
- ✨ `40209d4` feat(website): align design with identity manual
- ✨ `cc72ac9` feat(website): polish public bento design
- ✨ `d98a781` feat(website): fase 1-3 — hotfix navbar, mejoras UI Bento, mapa ADN Yucatán
- 🐛 `340f758` fix(medicine_depot_website): avoid sass unit comparison
- ✨ `0370922` feat(medicine_depot_website): refine public site design
- 🐛 `ba89d13` fix(medicine_depot_website): harden homepage xpath anchors
- ✨ `1bfcbb7` feat(medicine_depot_website): bento grid responsive + MedicD form + socios mejorados
- ✨ `f2a460d` feat(medicine_depot_website): Fase 1 — módulo completo de sitio web
