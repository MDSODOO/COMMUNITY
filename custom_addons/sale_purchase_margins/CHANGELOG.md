# Changelog — sale_purchase_margins

Historial generado automáticamente a partir de `git log -- sale_purchase_margins`. No es prosa editorial: cada línea es un commit real. Mantener actualizado: después de modificar este módulo, anteponer la entrada nueva bajo la fecha de hoy (o crear el día si no existe).

**Commits registrados:** 44 | **Rango:** 2026-05-16 → 2026-06-29

---


## 2026-06-29

- 🔧 `af60e60` chore(repo): limpieza jerárquica y reorganización de archivos raíz

## 2026-06-19

- 🔄 `4bcab86` refactor(server_management_ogum): resolver warnings de odoo 19 incluyendo descripciones, seguridad, tipos booleanos y widgets mal ubicados

## 2026-06-15

- 🐛 `f8bb363` fix(purchase_invoice_parser): implementar soporte multisucursal y reactividad real-time en notificaciones de precio

## 2026-06-14

- ✨ `ed69fa6` feat(purchase_invoice_parser): notificaciones con link al producto, boton aplicar precio y polling

## 2026-06-12

- 🐛 `0858d9e` fix(sale_purchase_margins): mover actualización de último costo y restaurar lots
- 🔄 `b08d4dd` refactor(md_lots_management): desactivar auto-margen y automatizar actualización de último costo de proveedor al recibir mercancía
- ✨ `ea229c7` feat(sale_purchase_margins): agregar historial automático de costos de entrada y facturación en formulario de producto
- 🐛 `c5e515c` fix(sale_purchase_margins): corregir nombre del modelo a stock.warehouse.orderpoint para resolver TypeError en registro

## 2026-06-11

- 🐛 `9adb200` fix(sale_purchase_margins): agregar purchase_stock a depends para garantizar stock.orderpoint en registry
- ✨ `099a5d7` feat(sale_purchase_margins): añadir acción en reabastecimiento para actualizar precio de venta basado en margen de compra

## 2026-06-10

- ✨ `6256359` feat(global): agregar i18n/es_MX.po a 11 módulos
- 📚 `678aa01` docs(global): auditoria de modulos, actualizacion de documentacion, propuesta de engine v2 y estructura inicial de manuales visuales para usuarios

## 2026-06-01

- 🔄 `0d8d5a2` refactor(account): reestructuracion de logica financiera resolviendo hallazgos criticos del reporte de auditoria

## 2026-05-27

- 🐛 `7de40da` fix(core): reubicacion de variables de traduccion en portal controller, fix de dependencias en medicine_depot_portal y asignacion de _name en modelo de picking

## 2026-05-26

- 🔄 `16ac4d3` refactor(sale_purchase_margins): audit performance + DRY policy logic

## 2026-05-20

- ✨ `5962079` feat(sale_purchase_margins): actualizar list_price al confirmar orden de venta
- 🔄 `ee94dfe` refactor(sale_purchase_margins): optimizar resolución de reglas de margen y corregir edge cases
- 🔧 `206d3c1` chore(project): actualizar estado del engine en CLAUDE.md y plan de mejoras de margenes
- 🔄 `e3f6925` refactor(migration): replace _sql_constraints with models.Constraint

## 2026-05-19

- 🐛 `fde5ac0` fix(margins): correccion de external ID en res_config_settings_view y adicion de dependencias en manifest para evitar ParseError
- ✨ `3efa333` feat(sale_purchase_margins): implementar fases 1 y 2 del plan de mejoras arquitectonico
- ✨ `2146228` feat(sale_purchase_margins): ejecutar plan de mejora de margenes con reglas por compania y politica de repricing

## 2026-05-18

- 🐛 `7d84060` fix(sale_purchase_margins): agregar prueba de regresion y documentar bridge de producto
- 🐛 `4143dee` fix(core): correccion de herencia/metodo en product.product para resolver ParseError en vistas nativas de website_sale
- 🐛 `cc09aa6` fix(sale_purchase_margins): endurecer validaciones de margen y limpiar UI
- ✨ `8766c2a` feat(sale_purchase_margins): reglas por linea y precio automatico por margen
- ✨ `9a52063` feat(sale_purchase_margins): mejorar notificación en chatter al actualizar precio de venta
- 🐛 `4e240fd` fix(sale_purchase_margins): erradicar product_uom inválido en sale.order.line y tests
- 🐛 `24bbb8b` fix(sale_purchase_margins): corregir dependencia inválida en @api.depends de _compute_qfm_purchase_margin
- 🐛 `b4a506e` fix(sale_purchase_margins): aplicar list_price automáticamente al validar recepción
- 🐛 `5b4741c` fix(fase-3): robustecer XPath expressions frágiles en 4 módulos
- 🔧 `9f9e55d` chore(sale_purchase_margins): agregar pruebas de regresion de margenes
- 🐛 `ce0b164` fix(sale_purchase_margins): re-raise UserError y ValidationError en bloques except
- 🐛 `5512e12` fix(sale_purchase_margins): blindar actualizacion automatica de list_price con sugerencia en chatter
- 🐛 `99c61ea` fix(manifest): adicion de clave license en manifest de modulos custom para resolver warnings de odoo en el arranque

## 2026-05-16

- 🐛 `d0352ad` fix(sale_purchase_margins): reescritura del hook usando write() para detectar estado done
- 🐛 `997a2dc` fix(sale_purchase_margins): correccion del hook y soporte para entradas directas de inventario
- ✨ `8b0dd5d` feat(sale_purchase_margins): actualizacion automatica de precio de venta al recibir compras
- 🐛 `17a7686` fix(sale_purchase_margins): correccion de bugs detectados en auditoria
- 🐛 `9978dbb` fix(margins): solucion definitiva a valueerror en compute method aplicando estandares de ORM para odoo 19 tras investigacion tecnica
- 🐛 `cb77b66` fix(margins): reescritura bulletproof del compute para prevenir ValueError en onchange de NewId
- 🐛 `1d80d14` fix(margins): refactorizacion de metodo compute para margin_pct asegurando asignacion por defecto y previniendo ValueError en onchange
- 🐛 `900e8ba` fix(sale_purchase_margins): refactorizacion de xpath en vistas de sale y purchase para compatibilidad con odoo 19 y resolucion de ParseError
- ✨ `9cf1113` feat(sale_purchase_margins): agregar módulo de márgenes de venta y compra
