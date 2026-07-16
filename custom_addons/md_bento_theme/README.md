# md_bento_theme — v19.0.1.0.8

**Categoría**: Website/Theme | **Licencia**: LGPL-3

## Propósito

Tema visual corporativo de Medicine Depot para la tienda online y el sitio público. Implementa el lenguaje de diseño **Bento-box + Glassmorphism** ("Liquid Glass") con las paletas de color y tipografía de la marca.

Controla:
- Layout global del sitio (`views/layout.xml`)
- Homepage con secciones bento
- Vistas de tienda (`/shop`, producto, carrito)
- Templates de afiliación (`/afiliacion`)
- Tipografía, gradientes y animaciones CSS
- Carrusel de marcas (socios)

## Dependencias

```python
depends = ['website', 'website_sale', 'medicine_depot_portal', 'custom_shop_qty_selector']
```

## Estructura de archivos

| Archivo | Propósito |
|---|---|
| `views/layout.xml` | Template base del sitio — header, footer, nav |
| `views/homepage.xml` | Secciones bento de la página principal |
| `views/shop_templates.xml` | Grid de productos y filtros de la tienda |
| `views/product_templates.xml` | Página de detalle de producto |
| `views/affiliate_templates.xml` | Página de afiliación |
| `views/snippets.xml` | Snippets de constructores (Odoo Website Builder) |
| `views/snippets/s_socios.xml` | Snippet del carrusel de marcas/socios |

## Assets estáticos

| Ruta | Contenido |
|---|---|
| `static/src/scss/` | Variables de marca, glassmorphism, bento grid, tipografía |
| `static/src/js/` | Animaciones y comportamientos interactivos |

## Notas de diseño

- Paleta: gradiente azul-azul oscuro para fondos, blanco frosted-glass para cards
- Tipografía: Inter (headings), sistema sans-serif (body)
- Login: card centrada con fondo de gradiente — sin espacio muerto lateral
- Breakpoints: mobile-first, con ajustes para tablet (768px) y desktop (1200px)

## Actividad reciente (rama test)

Los commits más recientes cubren:
- Rediseño del layout de login para eliminar espacio muerto
- Unificación del diseño Liquid Glass en `/my` y footer global
- Restauración del carrusel de marcas con diseño glassmorphism
- Normalización de tipografía y tamaños de heading en todo el sitio

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: md_bento_theme]
