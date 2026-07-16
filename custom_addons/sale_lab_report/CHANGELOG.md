# Changelog - sale_lab_report

## [19.0.1.0.0] - 2026-07-02
### Added
- Menú "Ventas Laboratorio" (Ventas > Reportes): pivot de `sale.report`
  preconfigurado por Producto/Sucursal (`warehouse_id`) y mes, con filtro
  por defecto para las líneas SERRAL, RAAM, PERRIGO - QUIFA, LIFERPAL,
  GELCAPS/PHARMACAPS y CMD (`product.template.x_studio_line`).
- Campos técnicos confirmados en vivo vía XML-RPC contra staging antes de
  escribir el XML (evitando repetir el error histórico de
  `purchase_invoice_parser` al harcodear `x_studio_linea_id`, que no
  coincidía con el campo real `x_studio_line`). Ver
  `docs/audits/2026-07-02_ventas_laboratorio_field_discovery.md`.

### Fixed
- Versión del manifest corregida de `19.1.0.0.0` a `19.0.1.0.0` (serie
  incorrecta generada por la plantilla `create-module.sh`): el servidor
  marcaba el módulo como `uninstallable` (`latest_version: False`) al
  no coincidir con la serie real de Odoo (19.0), aunque el resto del
  manifest se leía correctamente. Confirmado en vivo vía XML-RPC contra
  staging: todos los demás módulos custom instalados en esa base usan
  `19.0.x.y.z`.

### Changed
- Rediseño del pivot a pedido del usuario, replicando el patrón de uso que
  mostró en el reporte nativo "Análisis de ventas": filas = Producto
  (antes Producto+Sucursal anidado), columnas = Sucursal vía `company_id`
  (antes `date:month`). Se descubrió que `warehouse_id` no servía como
  "Sucursal" en esta base porque todas las ventas quedan bajo un único
  almacén ("MDS MERIDA"); los nombres reales de sucursal viven en
  `res.company` (multi-compañía, no multi-almacén).
- Vista de búsqueda reescrita de "heredada de sale.view_order_product_search"
  a standalone minimalista: seis `<filter>` individuales (uno por línea de
  laboratorio, combinables vía OR) más el filtro nativo de fecha. Se quitó
  el filtro combinado con las 6 líneas aplicado por defecto — ahora el
  usuario elige explícitamente qué línea(s) ver, sin otros filtros/group by
  expuestos.
- Se agregaron defaults de contexto para la vista `graph` (`graph_groupbys:
  ['company_id']`, `graph_measure: 'product_uom_qty'`, `graph_mode: 'bar'`)
  para que los mismos filtros de Línea/Fecha produzcan un gráfico útil (por
  Sucursal, máximo 6 barras) en vez de caer en el default de Odoo de agrupar
  por Fecha.
