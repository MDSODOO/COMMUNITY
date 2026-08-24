# Changelog — supplier_price_comparison

Historial generado automáticamente a partir de `git log -- supplier_price_comparison`. No es prosa editorial: cada línea es un commit real. Mantener actualizado: después de modificar este módulo, anteponer la entrada nueva bajo la fecha de hoy (o crear el día si no existe).

**Commits registrados:** 28 | **Rango:** 2026-05-28 → 2026-06-29

---

## 2026-07-01

- 🐛 `(pendiente commit)` fix(supplier_price_comparison): mover overrides de dark mode de `price_comparison.scss` a nuevo `backend_dark.scss` (bundle `web.assets_web_dark`) — el selector `.o_dark_mode` nunca coincidía con el DOM real de Odoo 19, dejando las tarjetas KPI/wizard/consolidador como "islas blancas" sobre el resto del backend ya oscuro. Ver `docs/audits/2026-07-01_backend_dark_mode_audit.md`.

## 2026-06-29

- 🔧 `af60e60` chore(repo): limpieza jerárquica y reorganización de archivos raíz

## 2026-06-19

- 🔄 `4bcab86` refactor(server_management_ogum): resolver warnings de odoo 19 incluyendo descripciones, seguridad, tipos booleanos y widgets mal ubicados

## 2026-06-10

- 🔧 `12d476b` chore(global): xml headers, cobertura de tests en 5 módulos y limpieza de TODOs
- ✨ `6256359` feat(global): agregar i18n/es_MX.po a 11 módulos
- 📝 `678aa01` docs(global): auditoria de modulos, actualizacion de documentacion, propuesta de engine v2 y estructura inicial de manuales visuales para usuarios

## 2026-06-02

- 🔄 `bba4059` refactor(backend): restauracion de light mode como tema base y encapsulacion de reglas oscuras en o_dark_mode

## 2026-06-01

- 🔄 `1983848` refactor(backend): refactorizacion de scss implementando css variables dinamicas para soporte nativo de light/dark mode
- 🐛 `3184106` fix(ui): dark mode tokens and backend contrast hardening
- 🔄 `26deeee` refactor(backend): refactorizacion de scss implementando css variables dinamicas para soporte nativo de light/dark mode
- 💄 `d966ea1` improvement(backend): sistema de design tokens y refactor UI Bento-box (29 mejoras)
- 🔄 `6b78ad4` refactor(core): actualizacion de sql_constraints a estandar odoo 19 y limpieza de modelos huerfanos detectados en logs
- 🐛 `6a66e6b` fix(wizard): refactorizacion para lectura dinamica de la primera hoja de excel evitando errores por nombres estaticos
- 🐛 `8dfa97b` fix(db): resolucion de conflictos de esquema y constraints para compatibilidad de despliegue en odoo.sh
- 🐛 `abcf433` fix(core): actualizacion de version en manifest a 19.0.x.x.x para resolver incompatibilidad y permitir instalacion
- 🔄 `ee0f843` refactor(price-comparison): focus module on excel consolidation flow
- ✨ `4909a36` feat(price-comparison): add supplier excel consolidation wizard

## 2026-05-29

- 🐛 `00d179b` fix(import): emparejamiento tolerante de barcodes para no duplicar productos legados
- 🐛 `fc8f642` fix(backend): correccion en la logica de extraccion y calculo para garantizar la carga de precios en la comparativa de proveedores
- 🐛 `48c6446` fix(import): rechazar barcodes no numericos y avisar cuando una importacion no procesa filas
- 🐛 `1d86138` fix(security): remocion de groups_id invalido en action_window y reubicacion de permisos de seguridad en el menu de historial de precios
- ✨ `7548127` feat(price-comparison): 29 mejoras — Bento/Glass, rendimiento, seguridad y auditoría
- 🔄 `561f92c` refactor(price-comparison): cerrar brechas P0/P1/P2 del gap analysis

## 2026-05-28

- 🐛 `6a41d89` fix(supplier_price_comparison): remove deprecated search group tag in price lines search view
- 🐛 `27a3cd2` fix(supplier_price_comparison): remove deprecated search group tag for Odoo 19
- 🐛 `bbde29b` fix(medicine_depot_supplier_import): resolve menu load order and restore views
- 🔧 `0e734b2` chore(supplier_price_comparison): temporarily exclude views for model diagnostics
- 🐛 `d334fdf` fix(supplier_price_comparison): refactor tree views to list views for Odoo 19
- ✨ `e01f882` feat(supplier_price_comparison): add missing dependency module
