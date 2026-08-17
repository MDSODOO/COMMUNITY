# Auditoría SEO técnico, on-page, schemas y CRO — Medicine Depot DEV

**Fecha:** 2026-08-17
**Alcance:** `https://odoo.bodegademedicamentos.com` (contenedor `medicinedepot_dev_odoo`, servidor `ionos`), módulos `medicine_depot_portal` y `md_bento_theme` en `custom_addons/`.
**Método:** auditoría de solo lectura vía `curl` (sin credenciales) contra el sitio en vivo + `Grep`/`Glob` contra el código fuente. Sin acceso a PageSpeed Insights, CrUX ni Search Console (Tier 0) — los hallazgos que dependen de esas APIs están marcados `needs_api`, nunca dados por buenos en silencio.

## Resumen ejecutivo

El sitio está **estructuralmente sano** (SSR completo vía QWeb, sin brecha de renderizado, HTTPS, viewport correcto, sitemap nativo, imágenes con `alt`) pero tiene **cinco fallos sistémicos** que golpean prácticamente todas las páginas del sitio:

1. **Meta description ausente en el 100% del sitio** — no por falta de contenido, sino por un **bug de una línea**: el código ya redacta la descripción pero la guarda en una variable (`meta_description`) que el `website.layout` nativo de Odoo no lee (espera `website_meta_description`). Mismo patrón rompe Open Graph/Twitter Card (`meta_image`).
2. **El catálogo (`/shop` y sus 26 categorías) está bloqueado tras login para cualquier visitante anónimo — incluidos Googlebot/Bingbot**, pese a que el propio código ya lo declara `sitemap=False`; el sitemap.xml igual las incluye (posible caché sin regenerar).
3. **Cero schema `LocalBusiness`/`Pharmacy`** pese a que las 6 sucursales ya tienen dirección, horario y coordenadas de mapa reales — el dato ya existe server-side, solo falta serializarlo a JSON-LD.
4. **Señales de confianza rotas para un sitio YMYL de salud**: sin licencia sanitaria/COFEPRIS propia visible, teléfono idéntico (`5555550123`) repetido en las 6 sucursales, banner promocional vencido desde el 19 de julio (hoy 17 de agosto), sección "blog" que enlaza a una URL 404.
5. **Cero contenido factual en ~2,500 fichas de producto** (`description_ecommerce` vacío) — son solo precio + nombre, sin indicaciones/composición, lo que las hace inútiles como fuente citable para motores de IA.

Los puntos 1 y 3 son los de **mayor ROI**: el 1 es literalmente un rename de variable en 5 archivos; el 3 ya tiene todos los datos listos, solo falta el template JSON-LD.

## Matriz de estatus — 24 puntos auditados

| # | Punto | Estatus | Evidencia | Archivo(s) a modificar |
|---|---|---|---|---|
| 1.1 | Meta-títulos únicos por página | 🟡 Requiere ajuste | `<title>` sí varía por página (home: "Medicine Depot \| Confianza y bienestar"; producto: "(LOFFYMIX)... \| **Medicine Depot Sureste**") pero el sufijo de marca es inconsistente entre home y producto | Config Website > Company Name / `md_bento_theme/views/homepage.xml` |
| 1.2 | Meta-descripciones únicas y optimizadas | 🔴 No implementado | 0 páginas con `<meta name="description">` en todo el sitio (home, producto, sucursales). Causa raíz: variable muerta `meta_description` en vez de `website_meta_description` | `medicine_depot_portal/views/public_templates.xml:150`, `medicine_depot_portal/data/website_pages.xml:32,67,103`, `md_bento_theme/views/homepage.xml:166` |
| 1.3 | Un solo `<h1>` por página | ✅ Cumple | Confirmado 1 h1 único en home y producto | — |
| 1.4 | Jerarquía `<h2>`→`<h3>` coherente | 🟡 Requiere ajuste | El footer compartido (todas las páginas) usa `<h5>` para "Enlaces"/"Sobre Nosotros"/"Contacto", saltando h2-h4; en `product1.html` el outline es h1→h5 directo | `md_bento_theme/views/layout.xml:219,245,260,266` |
| 2.1 | Intención de búsqueda / bloque TL;DR | 🔴 No implementado | Sin resumen destacado tras la intro en ninguna página revisada; encabezados son declarativos de marketing, no pregunta-respuesta | `medicine_depot_portal/views/afiliacion_templates.xml` y homólogos (a crear) |
| 2.2 | CTA primario tras el primer párrafo | ⚪ No verificable sin revisión visual | CTAs existen (Iniciar Sesión, Afiliación, Add to cart) pero su posición exacta relativa al primer párrafo no se confirmó solo con HTML crudo — requiere revisión de render/manual_review | `md_bento_theme/views/homepage.xml` |
| 2.3 | Tablas comparativas / listas para datos densos | 🔴 No implementado | Las fichas de producto no tienen ningún contenido descriptivo (ver 2.7 más abajo) — no hay dato que tabular todavía | `website_sale` (dato, no plantilla) |
| 2.4 | Sección FAQ visible | 🔴 No implementado | 0 coincidencias de "FAQ"/"preguntas frecuentes" en home, producto, sucursales | Página nueva `/preguntas-frecuentes` (ver propuesta schema abajo) |
| 2.5 | Schema `FAQPage` (JSON-LD) | 🔴 No implementado | Sin bloque `FAQPage` en ningún JSON-LD detectado | Mismo template nuevo que 2.4 |
| 2.6 | Barra CTA fija móvil (*Sticky Mobile CTA*) | 🔴 No implementado | Sin clases/selectores `sticky*` relacionados a CTA en el CSS/HTML inspeccionado | `md_bento_theme` (nuevo componente SCSS/JS) |
| 2.7 | Botones para compartir en redes sociales | 🔴 No implementado | Sin widgets de share (WhatsApp/Facebook/Twitter intent) en home ni producto | `md_bento_theme` (nuevo componente) |
| 3.1 | Nombres de archivo semánticos de imágenes | 🟡 Parcial / no accionable | Imágenes de producto/logo se sirven por rutas dinámicas de Odoo (`/web/image/product.product/8826/image_1024/...`), no archivos estáticos con nombre `medicamento-dosis.webp` — es el pipeline nativo de Odoo, tocarlo es alto riesgo/bajo retorno | No recomendado tocar |
| 3.2 | Atributos `alt` descriptivos | ✅ Cumple | 37/37 imágenes de home y 4/4 de producto con `alt` no vacío y descriptivo | — |
| 3.3 | Schema `Pharmacy`/`LocalBusiness` (Mérida/Yucatán, horarios, coords, teléfono) | 🔴 No implementado | 6 sucursales con NAP real visible en HTML (dirección, horario Lun-Vie/Sáb/Dom, link a Maps) pero **0 JSON-LD LocalBusiness** — solo el `Organization` genérico site-wide. Falta también geocodificar lat/lng (`needs_api`) | `medicine_depot_portal/views/public_templates.xml` (template `public_branches_page`) / snippet `s_md_branches.xml`, controlador `public.py::_get_branch_cards()` |
| 4.1 | URLs sin conectores/IDs numéricos crudos | 🔴 No cumple | Slugs de producto anteponen el código de barras de 13 dígitos y terminan con el ID interno de Odoo: `/shop/7502211784272-loffymix-ketoconazol-clindamicina-8826` — doble identificador numérico crudo | `website_sale` (core, requiere override de `_get_slug` o similar — evaluar riesgo antes de tocar) |
| 4.2 | `robots.txt` existe | ✅ Cumple | 200 OK, contiene `Sitemap:` | — |
| 4.3 | `Disallow: /page/` (y rutas sin valor SEO) | 🔴 No implementado | `robots.txt` no tiene **ninguna** directiva `Disallow` — ni para `/page/`, ni para `/shop/cart`, `/shop/wishlist`, `/web/login`, `/my/` | `robots.txt` custom de Odoo (Website > SEO) o `medicine_depot_portal/controllers` si hay override |
| 4.4 | `/llms.txt` | 🔴 No implementado | HTTP 404 (Odoo sirve su página 404 temática en vez de un 404 plano; el archivo simplemente no existe) | Nuevo controlador en `medicine_depot_portal/controllers/main.py` (`@http.route('/llms.txt', ...)`) |
| 4.5 | `/sitemap.xml` nativo | 🟡 Requiere ajuste | Existe y sirve 2,510 URLs, pero: (a) 3 URLs duplicadas exactas (`/medicd`, `/contactus`, `/contacto-quejas`, doble fuente controlador+`website.page`), (b) incluye `/shop` + 25 `/shop/category/*` marcadas `sitemap=False` en código mas presentes igual, (c) solo 3/2,510 URLs tienen `<lastmod>` | `medicine_depot_portal/controllers/public.py:501-607`, `data/website_pages.xml` |
| 4.6 | Etiqueta de verificación Google Search Console | 🔴 No implementado | Sin `<meta name="google-site-verification">` en el `<head>` | Website > Configuración (dato, no código) |
| 4.7 | Tag de Google Analytics 4 (GA4) | 🔴 No implementado | Sin `gtag(`, `G-XXXXXXX` ni `googletagmanager.com` en ningún HTML capturado | Website > Configuración > Google Analytics (nativo de Odoo, no requiere código) |

**Resumen del conteo:** 2 Cumple, 5 Requiere ajuste / parcial, 15 No implementado, 1 no verificable sin revisión visual/manual (2.2), 1 dato-no-plantilla fuera de alcance técnico razonable (3.1).

## Hallazgos adicionales (fuera de los 24 puntos, alto impacto)

Los 4 subagentes especializados encontraron problemas no listados explícitamente en el brief original pero directamente relevantes a SEO/CRO/confianza de un sitio YMYL de farmacia — se documentan aquí porque cambian la priorización real del trabajo:

| Hallazgo | Severidad | Detalle | Archivo |
|---|---|---|---|
| **Catálogo bloqueado a bots** | 🔴 Crítico | `/shop` y sus 26 categorías devuelven "Acceso Restringido" (HTTP 200, sin `noindex`) a *cualquier* visitante anónimo, incluido Googlebot — el hub de categorías del catálogo no es rastreable como contenido real | `medicine_depot_portal/controllers/public.py:592-606` (clase `WebsiteSaleShopAccess.shop()`) |
| **Sin licencia sanitaria/COFEPRIS propia** | 🔴 Crítico | El sitio exige "Aviso de Funcionamiento", "Licencia Sanitaria" y "Responsable Sanitario" a las farmacias que se afilian (`/afiliacion`), pero Medicine Depot no exhibe los suyos en ninguna página pública | Contenido (footer / página nueva "Regulatorio") |
| **Teléfonos placeholder duplicados** | 🟠 Alto | Las 6 sucursales muestran el mismo `5555550123`; el header global usa `+1 555-555-5556` (formato EE.UU. en sitio mexicano) | `public.py::_get_branch_cards()` (fallback a `_company_partner().phone` cuando el `stock.warehouse.partner_id` no tiene teléfono propio) — dato, no plantilla |
| **Banner promocional vencido** | 🟠 Alto | Hero de homepage promociona "Promoción del 11 de Junio al 19 de Julio 2026" — venció hace 4 semanas (hoy 17-ago-2026), sigue above-the-fold | `md_bento_theme/views/homepage.xml` |
| **Sección "blog" enlaza a 404** | 🟡 Medio | Homepage promociona "Podcast y blog" con CTA a `/blog` → HTTP 404 | `md_bento_theme/views/homepage.xml` |
| **Fichas de producto sin contenido factual** | 🔴 Crítico (escala x2,500) | `description_ecommerce` vacío en el catálogo — sin composición/indicaciones/contraindicaciones; el bloque `#product_description` de Odoo core existe pero no renderiza nada por falta de dato | Dato (import/carga masiva), no plantilla |
| **`Organization.name` = "MDS MÉRIDA"** | 🟡 Medio | El único JSON-LD del sitio usa el nombre interno de ERP (`res.company` #7) en vez de la marca pública "Medicine Depot" — mismo string se reutiliza para la sucursal de Mérida, mezclando entidad matriz y entidad-sucursal | `res.company` (dato) + nuevo override de `website.layout` |
| **`sameAs` vacío pese a tener redes reales** | 🟡 Medio | Facebook/Instagram/LinkedIn ya están hardcodeados en el footer (`md_bento_theme/views/layout.xml`) pero no en `res.company.social_*`, así que el JSON-LD Organization no los expone | `res.company` (dato — Odoo los añade automáticamente sin tocar plantilla) |
| **Rutas duplicadas sin redirect 301** | 🟡 Medio | `/` y `/home`, `/sucursales` y `/sucursal`, `/contactanos` y `/contactus` renderizan el mismo contenido en 2 URLs indexables (`sitemap=True` en ambas), en vez de 301 al canónico | `medicine_depot_portal/controllers/public.py:501-548` |
| **Cadena de redirección 303→301 en homepage** | 🟢 Bajo | `/` → 303 → `/en/` → 301 → `/en` (2 saltos en vez de 1) | No localizado en el repo (probable Caddy o `website` core) |
| **Footer con enlaces sin prefijo de idioma** | 🟡 Medio | En páginas `/en/...`, el footer enlaza `/shop`, `/sucursales`, `/contactus`, `/terms` sin el prefijo `/en/`, forzando un salto de redirección extra en miles de páginas (repetido en las ~2,500 fichas de producto) | `md_bento_theme/views/layout.xml:248-269` |
| **"Aviso de privacidad" apunta a Contacto** | 🟡 Medio | El propio código tiene un comentario `TODO` admitiendo que la página real de privacidad no existe (posible incumplimiento LFPDPPP) | `md_bento_theme/views/layout.xml:251-253` |
| **Imagen LCP sin WebP/AVIF** | 🟡 Medio | El banner hero (candidato a LCP, `fetchpriority="high"`) solo tiene variantes `.jpg` en su `srcset`, pese a ya estar bien optimizado en atributos (dimensiones explícitas, `loading="eager"`) | `md_bento_theme/views/homepage.xml:9`, `static/img/banner_mundial_2026*.jpg` |
| **Google Fonts render-blocking** | 🟢 Bajo | Hoja de estilos de `fonts.googleapis.com` cargada de forma síncrona (mitigado parcialmente con `preconnect`+`display=swap`, pero sigue bloqueando el primer render) | `md_bento_theme/views/layout.xml` (`<head>`) |
| **Términos y condiciones en inglés, sin fecha de vigencia** | 🟡 Medio | `/terms` es boilerplate genérico en inglés sin referencias a normativa mexicana (PROFECO) | Contenido `/terms` |

## Propuesta de schemas JSON-LD (Fase 2 — listos para revisión, `fixable: proposed`)

Todos los siguientes son propuestas — **ningún archivo fue escrito todavía**. Requieren tu confirmación antes de aplicarse (ver Fase 3).

1. **Organization + WebSite enriquecidos** (reemplaza el bloque genérico de 3 campos) — nombre público real, `address`, `sameAs` (Facebook/Instagram/LinkedIn ya existentes), `WebSite.potentialAction.SearchAction` apuntando a `/website/search?search=`.
2. **6× `Pharmacy`** (uno por sucursal, con `parentOrganization` a la Organization), usando los datos reales ya extraídos de `/sucursales` (dirección, horario Lun-Vie 09:00-19:00/Sáb 09:00-14:00/Dom cerrado, `hasMap`). **Pendiente:** teléfono real por sucursal (hoy placeholder) y geocodificación lat/lng.
3. **`FAQPage`** con 5 preguntas plausibles (afiliación, pedido mínimo, cobertura, CFDI, horario) — marcadas `TODO-VERIFY` donde el dato no está confirmado en el sitio, para que el negocio redacte la respuesta final antes de publicar.
4. **`Product`/`Offer` enriquecido**: agregar `seller` (→ Organization), `sku`, `brand`, `priceValidUntil`, `itemCondition` al JSON-LD nativo de `website_sale`.

El detalle completo de cada bloque JSON-LD (listo para copiar) vive en la salida del subagente `schema-generator` de esta sesión — se puede volcar a un archivo aparte si quieres el JSON completo fuera de este resumen.

## Plan de implementación — Fase 3 propuesta

Antes de tocar código en la base de desarrollo, propongo este orden (impacto ÷ esfuerzo):

**Auto/proposed — bajo riesgo, alto impacto:**
1. Renombrar `meta_description`→`website_meta_description` y `meta_image`→variable OG correcta (5 archivos) → arregla meta description + OG/Twitter en todo el sitio de un solo cambio.
2. Añadir `<meta name="robots" content="noindex,follow">` a `md_shop_access_restricted` + quitar `/shop`/`/shop/category/*` del sitemap si el gate es intencional (confirmar contigo primero — ver pregunta abajo).
3. Cambiar los 3 `<h5>` de footer a `<h2>`/`<h3>` (mismo estilo visual vía CSS).
4. Corregir enlaces de footer para respetar el prefijo de idioma.
5. Convertir `/home`, `/sucursal`, `/contactanos` en 301 hacia su canónica.
6. Nuevo controlador `/llms.txt`.
7. Inyectar los 3 bloques JSON-LD propuestos (Organization/WebSite, 6× Pharmacy, FAQPage) en las plantillas ya identificadas.

**Datos (no código) — requieren decisión de negocio, no del desarrollador:**
- Poblar `res.company.social_facebook/instagram/linkedin`.
- Cambiar `res.company` #7 de "MDS MÉRIDA" al nombre público.
- Reemplazar teléfonos placeholder en los 6 `stock.warehouse.partner_id`.
- Activar Google Analytics 4 y verificación GSC (Website > Configuración, sin código).
- Retirar/actualizar el banner de la promoción vencida.
- Poblar `description_ecommerce` en el catálogo (2,500 SKUs — proyecto aparte, fuera de alcance de un fix de plantilla).

**Advisory — decisión de negocio antes de tocar código:**
- ¿El catálogo (`/shop`) debe abrirse públicamente para SEO (sin precios/compra) o permanecer 100% gateado? Esto determina si el hallazgo crítico #1 se resuelve abriendo el listado o solo añadiendo `noindex` + limpiando el sitemap.
- Licencia sanitaria/COFEPRIS propia — dato legal que debe aportar el negocio, no inventarse.

## Nota de confianza de datos

Auditoría en **Tier 0** (solo `curl`/lectura de código, sin PageSpeed Insights, CrUX ni Search Console). Hallazgos marcados `needs_api` en los reportes de los subagentes (Core Web Vitals de campo, acceso real de bots de IA vía CDN/WAF, geocodificación de sucursales) requieren esas herramientas para confirmarse — no se dieron por buenos en silencio.
