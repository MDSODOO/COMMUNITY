# l10n_mx_sat_account

Primera pieza de "Contabilidad Electrónica" (SAT México) que no existe en
ningún lado de Community/OCA (verificado a fondo: 20 módulos de
`OCA/l10n-mexico` revisados, cero coincidencias).

## Qué trae

- `l10n_mx.sat.account.group.code`: tabla de referencia con el código
  agrupador completo del **Anexo 24 de la RMF vigente** (DOF, 13 de enero
  de 2026 — fuente oficial primaria, transcrita directamente del PDF
  publicado por el SAT, no de un tercero). ~1080 códigos entre rubros,
  cuentas de nivel mayor y subcuentas.
- Campo `l10n_mx_sat_group_code_id` en `account.account` para mapear cada
  cuenta al código correspondiente.
- Wizard (Facturación > Reportes > "Catálogo de Cuentas (XML SAT)") que
  genera el XML del Catálogo de Cuentas en el esquema real del SAT
  (`Catalogo`/`Ctas`, namespace
  `http://www.sat.gob.mx/esquemas/ContabilidadE/1_1/CatalogoCuentas`,
  confirmado contra el XSD oficial publicado por el SAT).

## Qué NO trae (limitaciones reales, no ocultarlas)

- **Sin sellado digital**: el XSD permite `Sello`/`Certificado`/
  `noCertificado` como opcionales, pero un envío real al SAT los
  requiere. Este módulo no firma nada — genera el XML sin sellar.
- **Nivel simplificado a 1 para todas las cuentas**: no se modela la
  jerarquía real de subcuentas (`SubCtaDe`) de cada compañía. Si el
  contribuyente maneja subcuentas jerárquicas reales, esto requiere
  revisión antes de un envío real.
- **Balanza de Comprobación y Pólizas quedan fuera** de este módulo —
  son la siguiente pieza, no construida aquí.
- El mapeo cuenta → código agrupador es manual (no hay auto-mapeo por
  heurística) — cada compañía tiene que asignarlo cuenta por cuenta.

Ver `docs/plans/PLAN_ADAPTACION_CONTABILIDAD_COMMUNITY.md` en el repo
principal de Medicine Depot para el contexto completo.
