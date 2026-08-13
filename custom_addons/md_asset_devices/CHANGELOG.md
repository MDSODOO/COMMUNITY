# Changelog — md_asset_devices

Historial generado automáticamente a partir de `git log -- md_asset_devices` (y `quifamesa_it_management` antes del renombre). No es prosa editorial: cada línea es un commit real. Mantener actualizado: después de modificar este módulo, anteponer la entrada nueva bajo la fecha de hoy (o crear el día si no existe).

**Commits registrados:** 14 | **Rango:** 2026-06-20 → 2026-06-21

> ⚠️ Este módulo se llamó `device_management_ogum` hasta el commit `d9775ab` (2026-06-21), que lo renombró a `quifamesa_it_management`, y el 2026-08-13 se renombró de nuevo a `md_asset_devices` para alinearlo a la convención `md_*` de Medicine Depot. El historial abajo incluye los commits previos a ambos renombres.

---

## 2026-08-13

- 🔄 refactor(md_asset_devices): renombrar módulo (`quifamesa_it_management` → `md_asset_devices`), quitar referencias textuales a Quifamesa y agregar campo `company_id` (sucursal) con regla multi-compañía para operar en las 6 sucursales de Medicine Depot
- 🐛 fix(md_asset_devices): `<group expand="0" string="...">` en la vista de búsqueda ya no valida en este build de Odoo 19 — se quitan esos atributos
- 🐛 fix(md_asset_devices): `_sql_constraints` deprecado → migrado a `models.Constraint`; labels duplicados de `maintenance_count`/`payment_count`/`subscription_count` vs sus `_ids`; `title` agregado a 10 íconos `<i class="fa ...">` del kanban (a11y)
- ✨ feat(md_asset_devices): ícono de app cambiado a FontAwesome (`fa-laptop,#2C3E50,#EAECEE`, antes PNG genérico heredado de Quifamesa); nombre de la acción "IT Management" → "Dispositivos IT"
- 🎨 refactor(md_asset_devices): UI — consolidados los smart buttons de "vencidos/urgentes" (Mant. vencidos, Docs vencidos, Subs vencidas, Urgentes) como badges superpuestos en su botón padre en vez de botones separados (10→6 botones); alertas de vencimiento en kanban ahora mutuamente excluyentes con su alerta "próximo" equivalente; quitado bloque de garantía duplicado (y un `<group>` vacío) en la pestaña General — esa info ya vive en el snapshot superior


## 2026-06-21

- 🔄 `d9775ab` refactor(quifamesa_it): renombrar modulo, resolver errores de accesibilidad a11y en labels y modernizar ui/ux del backend
- 📚 `921e1b2` docs(device_management): agregar manual, auditoría UI/UX con Playwright y screenshots del módulo
- 🐛 `cceafed` fix(quifamesa_it): aplicar minimal viable view para destrabar error de validacion RNG y reconstruir busqueda de dispositivos
- 🐛 `b7fcee3` fix(quifamesa_it): reconstruir vista de busqueda device.management.search para eliminar dominios invalidos y resolver error de esquema RNG
- 🐛 `2fe5405` fix(quifamesa_it): reparar error de sintaxis estricta xml en la definicion de la vista de busqueda
- 🐛 `779f9e8` fix(quifamesa_it): reparar error de sintaxis en vista de busqueda y limpiar parametros invalidos unique, tracking y widget en modelos python
- 🐛 `ea2fee1` fix(quifamesa_it): refactorizar dominios de busqueda para campos calculados como garantia_vigente evitando crash del ORM
- 🐛 `561a5a4` fix(quifamesa_it): corregir filtro de busqueda en campos calculados agregando metodos de busqueda o store=True para evitar crash en actualizacion
- 🔄 `11a5e05` refactor(quifamesa_it): auditar funcionalidad con playwright, automatizar logica de modelos y mejorar experiencia de usuario ui/ux
- 🐛 `1fc351b` fix(quifamesa_it): agregar dependencia mail y remover widget one2many_list obsoleto para limpiar advertencias OWL en consola

## 2026-06-20

- 🐛 `c9a3409` fix(device_management): eliminar importaciones prohibidas en ir.cron usando el entorno seguro de Odoo para evitar error safe_eval
- 🐛 `b5d0e74` fix(device_management): eliminar campo obsoleto doall en ir.cron para permitir instalacion en Odoo 19
- 🔄 `068c11d` refactor(device_management): fix account.invoice obsolete model, improve relational logic, and upgrade UI with smart buttons and ribbons
- ✨ `a1616fa` feat(device_management_ogum): crear estructura base para gestión de dispositivos con control de inventario A la Mano
