# Changelog — medicine_depot_scrap_batch

Historial generado automáticamente a partir de `git log -- medicine_depot_scrap_batch`. No es prosa editorial: cada línea es un commit real. Mantener actualizado: después de modificar este módulo, anteponer la entrada nueva bajo la fecha de hoy (o crear el día si no existe).

**Commits registrados:** 47 | **Rango:** 2026-05-24 → 2026-06-30

---


## 2026-06-30

- 🐛 fix(medicine_depot_scrap_batch): crear paperformat con header_spacing=0 — elimina espacio en blanco superior en Orden de Bajas y Consolidado [19.0.1.2.3]
- 🎨 refactor(medicine_depot_scrap_batch): refactorizar layout de consolidado — eliminar pharma-body-address-shell del foreach, migrar totales a inv-total-table, reducir firma a 2rem
- 🐛 fix(medicine_depot_scrap_batch): columna TH renombrada a "CANTIDAD A LA MANO DADA DE BAJA" (mayúsculas per regla A la mano)
- 🐛 fix(pharma_reports): agregar stock.scrap.batch a guards de layout — root cause del doble header en consolidado
- 🐛 fix(medicine_depot_scrap_batch): t-foreach para o en scope exterior — corrige header nativo en consolidado [1.2.2]
- 🐛 fix(medicine_depot_scrap_batch): botón PDF en form apunta a consolidado, ícono fa-file-pdf-o, versión 1.2.1
- 🐛 `24ea4d7` fix(medicine_depot_scrap_batch): corregir header duplicado siguiendo patrón pharma_reports
- 🐛 `19189f8` fix(medicine_depot_scrap_batch): unificar reportes y eliminar header duplicado

## 2026-06-29

- 🔧 `af60e60` chore(repo): limpieza jerárquica y reorganización de archivos raíz

## 2026-06-19

- 🔄 `4bcab86` refactor(server_management_ogum): resolver warnings de odoo 19 incluyendo descripciones, seguridad, tipos booleanos y widgets mal ubicados

## 2026-06-13

- 🐛 `cc3110b` fix(dark-mode): eliminar dark mode POS + forzar statusbar scrap_batch oscuro
- 🐛 `cb6c816` fix(dark-mode): pos-force-light para iface_theme + statusbar scrap_batch en dark mode
- 🐛 `c382591` fix(dark-mode): migrar dark mode de scrap_batch a bundle web.assets_web_dark + fix texto tarjetas POS
- 🐛 `c06a5dd` fix(medicine_depot_scrap_batch): agregar selector data-bs-theme="dark" para dark mode en Odoo 19
- 🐛 `ecb19eb` fix(medicine_depot_scrap_batch): neutralizar color de links en valores KPI para consistencia visual

## 2026-06-11

- ✨ `1b0f904` feat(medicine_depot_scrap_batch): agregar reporte PDF consolidado global de bajas por día
- ✨ `2373bb6` feat(medicine_depot_scrap_batch): mejorar diseño UI similar a md_lots_management
- ✨ `81b1369` feat(medicine_depot_scrap_batch): unificar UI con md_lots_management y agregar sucursal y cantidad a la mano
- 🐛 `ee91e4d` fix(medicine_depot_scrap_batch): hacer visible el field company_id en form sin restricciones de grupo
- 🐛 `74a08e0` fix(purchase_invoice_parser, medicine_depot_scrap_batch): corregir validación de unicidad de lotes en entorno multiempresa

## 2026-06-10

- ✨ `6256359` feat(global): agregar i18n/es_MX.po a 11 módulos
- 📚 `678aa01` docs(global): auditoria de modulos, actualizacion de documentacion, propuesta de engine v2 y estructura inicial de manuales visuales para usuarios

## 2026-06-09

- 🐛 `0942e55` fix(scrap_batch): renombrado de strings duplicados en modelos de bajas para resolver warnings de ir_model en odoo 19

## 2026-06-06

- 🐛 `abd8c4d` fix(medicine_depot_scrap_batch): usar XPath específicos para eliminar solapamiento de header en PDF
- 🐛 `ed50acb` fix(medicine_depot_scrap_batch): restaurar selectores XPath robustos para eliminar solapamiento en reportes PDF de bajas
- 🐛 `b644ad4` fix(reports): corrige superposicion de header nativo en reportes pdf

## 2026-06-02

- 🔄 `bba4059` refactor(backend): restauracion de light mode como tema base y encapsulacion de reglas oscuras en o_dark_mode

## 2026-06-01

- 🔄 `1983848` refactor(backend): refactorizacion de scss implementando css variables dinamicas para soporte nativo de light/dark mode
- 🐛 `3184106` fix(ui): dark mode tokens and backend contrast hardening
- 🔄 `26deeee` refactor(backend): refactorizacion de scss implementando css variables dinamicas para soporte nativo de light/dark mode
- • `d966ea1` improvement(backend): sistema de design tokens y refactor UI Bento-box (29 mejoras)

## 2026-05-29

- ✨ `cb57150` feat(inventory): renombramiento a Bajas de caducidad y adicion de exportacion PDF estandarizada para Acumulado del mes
- 🔄 `f445f79` refactor(ui): renombre de menu a Bajas de caducidad y unificacion de historial en un unico smart button

## 2026-05-28

- ✨ `45826e4` feat(inventory): restriccion de boton de validacion a administradores y creacion de regla ir.rule para aislamiento multi-compania en ordenes de bajas

## 2026-05-27

- 🐛 `0960f08` fix(medicine_depot_scrap_batch): make summary SQL view tolerant to missing stored cost column
- 🐛 `35cd3c8` fix(medicine_depot_scrap_batch): avoid undefined columns in legacy scrap view

## 2026-05-26

- 🐛 `e67cad1` fix(medicine_depot_scrap_batch): SCSS local-import bloqueado + UndefinedTable historial
- 🐛 `55e5812` fix(medicine_depot_scrap_batch): compatibilidad Odoo 19 — Command API y assets SCSS
- 🐛 `f184515` fix(medicine_depot_scrap_batch): aislar scope CSS de botones nativos de Odoo

## 2026-05-25

- ✨ `8dfba4b` feat(medicine_depot_scrap_batch): dashboard unificado y analítica legado
- 🐛 `adecca9` fix(medicine_depot_scrap_batch): quitar widget=date sobre campo Datetime
- 🔄 `13b81f2` refactor(medicine_depot_scrap_batch): form Bento — jerarquía y consistencia
- 🔄 `4d55d90` refactor(medicine_depot_scrap_batch): Acumulado del mes como menú con rango fecha
- 🐛 `203ec86` fix(medicine_depot_scrap_batch): purgar ir_model_data + cross-link dashboard
- 🐛 `9be00d1` fix(medicine_depot_scrap_batch): prevent unlink on summary SQL view
- 🐛 `0b1ff0c` fix(medicine_depot_scrap_batch): reemplazar int() por .year en domain de search
- 🐛 `148d55d` fix(medicine_depot_scrap_batch): dynamic scrap dashboard and UI refresh
- 🐛 `8f99cd1` fix(medicine_depot_scrap_batch): use dot-notation csv name for scrap summary model
- 🐛 `3486cf4` fix(medicine_depot_scrap_batch): align scrap summary csv with model name
- 🐛 `82de737` fix(medicine_depot_scrap_batch): UndefinedTable, UX historial y dashboard 2025
- ✨ `588d3b2` feat(medicine_depot_scrap_batch): dashboard visual con paleta corporativa y vistas QWeb
- ✨ `5be6b25` feat(medicine_depot_scrap_batch): sync scrap batch module

## 2026-05-24

- 🐛 `eb8a3a1` fix(medicine_depot_scrap_batch): expose post_init_hook at package level
- ✨ `243d506` feat(medicine_depot_scrap_batch): add module for multiple scrap batch orders
