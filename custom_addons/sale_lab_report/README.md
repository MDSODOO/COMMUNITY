# sale_lab_report

## Descripción
Añade el menú **Ventas Laboratorio** bajo **Ventas > Reportes**: una Tabla
Dinámica (Pivot) de `sale.report`, filas = Producto, columnas = Sucursal
(compañía), exportable a Excel con el botón de descarga nativo del pivot.

## Funcionalidades
- Búsqueda minimalista: lo único seleccionable por el usuario es la
  **Línea** (un checkbox por laboratorio — SERRAL, RAAM, PERRIGO - QUIFA,
  LIFERPAL, GELCAPS/PHARMACAPS, CMD — combinables entre sí) y la **Fecha de
  la Orden** (widget nativo de rango). No se exponen otros filtros/group by
  para mantener el reporte enfocado.
- Pivot con filas = Producto (`product_tmpl_id`) y columnas = Sucursal
  (`company_id`). Estos dos ejes son fijos (definidos en el contexto de la
  acción), no filtros que el usuario cambie.
- Exportación a Excel: usa el botón de descarga nativo del pivot de Odoo
  (icono ⬇ en la barra de herramientas) — no requiere código adicional.

## Instalación
Depende de `sale` y `sale_stock`. Requiere que el módulo Studio `x_line` y
el campo `product.template.x_studio_line` existan en la base de datos — si
no existen, los filtros de línea simplemente no devuelven resultados (no
rompe la instalación).

## Uso
Ventas > Reportes > Ventas Laboratorio. Marca el checkbox de la línea que
quieras analizar (y opcionalmente un rango de fecha), y el pivot se llena
con Producto en filas y Sucursal en columnas.

## Notas técnicas
- **"Sucursal" = `company_id`, no `warehouse_id`.** Se intentó primero con
  `warehouse_id` (nativo y estable en `sale.report`), pero en esta base de
  datos todas las ventas están registradas bajo un único almacén
  ("MDS MERIDA"), así que no distinguía nada. Los nombres reales de
  sucursal (MDS CAMPECHE, MDS CANCÚN, MDS CHETUMAL, MDS PLAYA DEL CARMEN,
  MDS TICUL, y la compañía raíz "SABRINA ELIZABETH ROJANO ROMERO") viven en
  `res.company` — confirmado en vivo por XML-RPC. Este es un caso de
  multi-compañía por sucursal, no multi-almacén.
- El campo `x_line.x_name` (nombre del laboratorio) puede traer espacios en
  blanco iniciales inconsistentes en los datos reales (ej. `' SERRAL'`); el
  domain de cada filtro de línea usa `ilike` en vez de `=`/`in` para
  tolerarlo.
- Confirmado por consulta en vivo (XML-RPC) contra la base de staging
  `medicinedepot-test-34376716` el 2026-07-02 — ver
  `docs/audits/2026-07-02_ventas_laboratorio_field_discovery.md`.

## Autor
Daniel-Cervera (daniel.cervera.2029@gmail.com)
