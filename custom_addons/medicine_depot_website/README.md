# medicine_depot_website — v19.0.1.2.0

**Categoría**: Website | **Licencia**: LGPL-3

## Propósito

Capa de sitio web público de Medicine Depot. Gestiona las páginas y secciones del sitio accesibles sin autenticación:

- Homepage con diseño bento
- Página del programa MedicD
- Página de sucursales
- API pública para integraciones externas (cotizaciones, consultas de catálogo)

Es la capa superior del front-end; depende de `medicine_depot_portal` para la infraestructura base de templates.

## Dependencias

```python
depends = ['medicine_depot_portal', 'crm']
```

## Modelos

### `res.config.settings` (extensión)
Agrega configuraciones del sitio web público (texto de bienvenida, datos de contacto visibles, etc.).

## Controllers

### `controllers/api.py`
API REST pública (sin autenticación requerida):
- `GET /api/v1/products` — Catálogo de productos con cantidad A la mano
- `POST /api/v1/affiliate` — Solicitud de afiliación (genera lead en CRM)

## Vistas / Páginas

| Archivo | Página |
|---|---|
| `views/pages/homepage.xml` | Página principal `/` |
| `views/pages/medicd.xml` | Programa MedicD `/medicd` |
| `views/snippets/s_md_hero.xml` | Snippet hero principal |
| `views/snippets/s_md_podcast.xml` | Snippet de podcast/video |
| `views/snippets/s_md_socios.xml` | Snippet de socios/marcas |
| `views/snippets/s_md_bento_grid.xml` | Grid bento de servicios |

## Tests

```bash
pytest medicine_depot_website/tests/test_medicine_depot_website.py -v
```

## Notas técnicas

- El módulo `crm` es requerido para el flujo de afiliación (crea `crm.lead` automáticamente)
- Los snippets registrados aparecen en el Website Builder bajo la categoría "Medicine Depot"
- La API pública usa `http.route(..., auth='public', cors='*')` — revisar CORS en producción

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: medicine_depot_website]
