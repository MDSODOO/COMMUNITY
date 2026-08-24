# ai_fields — v19.0.1.6.0

**Categoría**: Technical | **Licencia**: LGPL-3

## Propósito

Módulo técnico de mantenimiento que resuelve dos problemas de arranque en Odoo 19:

1. **Normalización de labels**: Renombra `x_studio_branch_office` de `"Sucursal"` a `"Sucursal (Oficina)"` para eliminar el warning `Duplicate labels` que genera Odoo 19 cuando dos campos del mismo modelo tienen la misma etiqueta visible.
2. **Sanitización de NULLs**: Ejecuta limpieza de `NULL` en columnas `NOT NULL` de `account`, `website`, `purchase` y `product` en cada arranque del servidor.

## Dependencias

```python
depends = ['base', 'sale']
```

## Modelos

### `ai.fields.null.sanitizer`

Modelo técnico (sin tabla real) que se ejecuta mediante `post_init_hook`. Corre queries SQL directos para convertir `NULL` → valor por defecto en columnas críticas.

## Archivos de datos

| Archivo | Contenido |
|---|---|
| `data/field_labels.xml` | Record `ir.model.fields` que sobreescribe la label de `x_studio_branch_office` |

## Migraciones

| Versión | Acción |
|---|---|
| 19.0.1.2.0 | Migración inicial de labels |
| 19.0.1.3.0 | Extensión a más campos |
| 19.0.1.4.0 | NULL sanitizer `purchase` |
| 19.0.1.5.0 | NULL sanitizer `website` |
| 19.0.1.6.0 | Consolidación final |

## Instalación / Actualización

Este módulo debe instalarse **antes** que cualquier otro módulo del proyecto. Se recomienda como primera dependencia en entornos nuevos.

```bash
# Instalar en Odoo
python odoo-bin -u ai_fields -d <base>
```

## Notas técnicas

- No genera vistas de usuario ni menús
- Sin datos de prueba en producción
- Compatible con migraciones en paralelo (las versiones de migración son idempotentes)

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: ai_fields]
