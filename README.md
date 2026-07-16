# MedicineDepot — Odoo 19 Community Migration

Proyecto de migración Enterprise → Community para MedicineDepot Sureste, corriendo en `ionos` (74.208.191.88). / Enterprise → Community migration project for MedicineDepot Sureste, running on `ionos` (74.208.191.88).

## Entornos / Environments

| Entorno | Puerto | Estado |
| --- | --- | --- |
| dev  | 8069 | Activo / Active |
| test | 8070 | Pendiente / Pending |
| prod | 8071 | Pendiente / Pending |

## Uso / Usage

```bash
cd /opt/medicinedepot-odoo19-migration
docker compose --env-file .env.dev up -d
docker compose --env-file .env.dev logs -f odoo
docker compose --env-file .env.dev down
```

## Módulos custom / Custom modules

Montados en `custom_addons/` (read-write en dev). El primer módulo planeado es `md_security_roles` (grupos, ACL y reglas de registro para los 4 roles operativos).

## Referencia / Reference

Auditoría de módulos y roles del entorno de producción original: ver `PRODUCTION_AUDIT.md`, `ROLE_MATRIX.md` y `ROLES_AND_PERMISSIONS.md` en `~/odoo-cfdi-audit/` (Mac local).
