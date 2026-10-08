# medicine_depot_portal — v19.0.2.10.0

**Categoría**: Website/Portal | **Licencia**: LGPL-3

## Propósito

Rediseño completo del Portal del Cliente (`/my`) con CSS Grid + Glassmorphism (Bento-box). Es el módulo central del front-end de clientes y provee:

- Dashboard del portal con tarjetas bento (pedidos, facturas, entregas)
- Flujo de **Afiliación** (`/afiliacion`) para nuevos clientes
- Módulo de **Farmacovigilancia** (reporte de reacciones adversas)
- Página restringida del shop para visitantes no autenticados
- Templates base de autenticación (login, signup) personalizados

Este módulo es la dependencia raíz de `medicine_depot_website`, `md_bento_theme` y `portal_picking_visibility`.

## Dependencias

```python
depends = [
    'portal', 'mail', 'sale_management', 'account',
    'stock', 'website', 'website_sale', 'auth_signup'
]
```

## Modelos

| Modelo | Archivo | Propósito |
|---|---|---|
| `website` | `models/website.py` | Configuración de tienda restringida |
| `medicine.depot.pharmacovigilance` | `models/pharmacovigilance.py` | Reporte de reacciones adversas |

## Controllers

| Archivo | Rutas |
|---|---|
| `controllers/portal.py` | `/my`, `/my/orders`, `/my/invoices`, `/my/pickings` |
| `controllers/public.py` | `/afiliacion`, `/farmacovigilancia` |
| `controllers/utils.py` | Helpers compartidos entre controllers |

## Vistas principales

| Archivo | Contenido |
|---|---|
| `views/portal_templates.xml` | Dashboard `/my` y sub-páginas |
| `views/auth_templates.xml` | Login, signup, reset password personalizados |
| `views/afiliacion_templates.xml` | Formulario y confirmación de afiliación |
| `views/pharmacovigilance_views.xml` | Form de farmacovigilancia |
| `views/shop_session_inherits.xml` | Página restringida del shop |
| `views/public_templates.xml` | Templates públicos generales |
| `views/snippets/` | 9 snippets Bento para Website Builder |

## Snippets disponibles

| Snippet | Propósito |
|---|---|
| `s_md_hero_bento` | Hero section bento con CTA |
| `s_md_service_grid` | Grid de servicios |
| `s_md_product_card` | Tarjeta de producto destacado |
| `s_md_audit_grid` | Grid de auditoría/métricas |
| `s_md_logos_ticker` | Ticker animado de logos |
| `s_md_wizard_hero` | Hero con wizard de búsqueda |
| `s_md_blog_grid` | Grid de artículos |
| `s_md_two_col` | Layout de dos columnas |
| `s_md_branches` | Mapa/lista de sucursales |

## Datos de configuración

| Archivo | Contenido |
|---|---|
| `data/auth_signup_config.xml` | Configuración del registro público |
| `data/website_pages.xml` | Páginas estáticas registradas |
| `data/website_menu.xml` | Estructura del menú del sitio |
| `data/pharmacovigilance_sequence.xml` | Secuencia para folios de farmacovigilancia |

## Tests

```bash
pytest medicine_depot_portal/tests/ -v
```

Cubre: templates de portal, redirección del dashboard, template de farmacovigilancia, flujo de afiliación, flujos de portal completos.

## Notas técnicas

- El shop restringido usa `website.is_public_user()` para redirigir a login
- La afiliación no crea usuario automáticamente — genera un lead en CRM
- Farmacovigilancia genera PDF y notifica al equipo médico por correo

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: medicine_depot_portal]
