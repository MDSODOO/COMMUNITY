# MedicineDepot — Odoo 19 Community Migration

Proyecto de migración Enterprise → Community para MedicineDepot Sureste, corriendo en `ionos` (74.208.191.88). / Enterprise → Community migration project for MedicineDepot Sureste, running on `ionos` (74.208.191.88).

## Entornos / Environments

| Entorno | Puerto | Estado |
| --- | --- | --- |
| dev  | 8069 | Activo / Active |
| test | 8070 | Activo / Active (2026-07-27) — base de datos propia (`medicinedepot_test`), vacía, workers=2 |
| prod | 8071 | Pendiente / Pending |

`test` corre como una pila Docker separada de `dev` (`docker-compose.test.yml`), con su propio Postgres, volúmenes y `config/odoo_test.conf` — comparte servidor con `dev` (8 CPU/15GB) por lo que usa `workers=2` en vez de 5 para no competir por CPU. Arrancó con base de datos vacía (solo `base` instalado); los módulos custom de `custom_addons/` aún no se instalaron ahí.

## Uso / Usage

```bash
cd /opt/medicinedepot-odoo19-migration

# dev
docker compose --env-file .env.dev up -d
docker compose --env-file .env.dev logs -f odoo
docker compose --env-file .env.dev down

# test
docker compose -f docker-compose.test.yml --env-file .env.test up -d
docker compose -f docker-compose.test.yml --env-file .env.test logs -f odoo
docker compose -f docker-compose.test.yml --env-file .env.test down
```

## Módulos custom / Custom modules

Montados en `custom_addons/` (read-write en dev) — 31 módulos a la fecha (2026-07-31). Los más relevantes:

- **`local_ai_connector`** — Copiloto de IA local (Ollama, servidor dedicado `mds_agent1`, aislado por UFW — ver `docs/AI_MODEL_ODOO_CONFIG.md`). Cuatro capacidades:
  - `qwen2.5-coder:7b`: copiloto ETL (scripts `xmlrpc.client`) y auditoría de compatibilidad de módulos — externo a Odoo, no expuesto vía HTTP.
  - `qwen2.5vl:7b-q8_0` (visión): extracción de productos desde fotos de cotizaciones escritas/impresas a mano (`/ai/quote_from_image`, público, con rate limit + validación de Origin/Referer; `/ai/quote_from_image_internal`, staff, exige contacto `res.partner` ya registrado) e identificación de un producto individual desde foto de empaque (`/ai/identify_product_from_photo`).
  - Consultas de inventario en lenguaje natural (`/ai/inventory_query`) — el LLM nunca es la fuente de verdad de una cantidad física; solo traduce la pregunta a una consulta estructurada y redacta la respuesta con el dato real de `stock.quant`.
  - Matching de producto por texto usa las extensiones Postgres `unaccent` + `pg_trgm` (instaladas vía `post_init_hook`/migración `19.0.1.1.0`) para tolerar acentos y errores de OCR/visión.
  - Regla inquebrantable en todo el módulo: la cantidad física de un producto se nombra únicamente **"A la mano"** (On Hand) — nunca "disponible", "stock" ni "existencias".
- `md_security_roles` — grupos, ACL y reglas de registro para los 4 roles operativos (primer módulo de la migración).

Detalle completo de la arquitectura de IA (servidores, modelos, latencias medidas, gobernanza de recursos, hallazgos de la auditoría 2026-07-31): `docs/AI_MODEL_ODOO_CONFIG.md`. El resto de los 31 módulos aún no está documentado aquí.

## Referencia / Reference

Auditoría de módulos y roles del entorno de producción original: ver `PRODUCTION_AUDIT.md`, `ROLE_MATRIX.md` y `ROLES_AND_PERMISSIONS.md` en `~/odoo-cfdi-audit/` (Mac local).
