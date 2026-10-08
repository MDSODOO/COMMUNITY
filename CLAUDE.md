# CLAUDE.md — medicinedepot-odoo19-migration

Snapshot versionado (sincronizado desde el servidor `ionos`, 74.208.191.88) del proyecto de migración Enterprise → Community de MedicineDepot Sureste: no es un repo de desarrollo activo desde cero, sino la copia de trabajo que se despliega directamente en ese servidor con `docker compose`.

## Levantar el entorno

Requiere un `.env.dev` local con `POSTGRES_PASSWORD` (y opcionalmente `POSTGRES_DB`, `POSTGRES_USER`, `ODOO_PORT`) — está en `.gitignore`, no viene en el repo y **no existe en este checkout**; hay que crearlo a mano antes de levantar nada. Ver skill `levantar-entorno`.

Módulos propios: prefijo `md_`/`medicine_depot_`. El resto (sin prefijo) son de terceros ya integrados al negocio. Nota: algunos de terceros (p. ej. `bi_pos_stock`) traen su propio `README.md`/`CHANGELOG.md`/`CLAUDE.md` del vendor upstream — son ajenos a esta documentación de proyecto, no los confundas con este archivo ni los edites como si fueran nuestros.

## Lint automático (hook)

`.claude/settings.json` corre un hook `PostToolUse` (`.claude/hooks/lint-python.sh`) tras cada edición de un `.py`: formatea con `black` (venv local en `.venv/`, line-length 100) y reporta problemas de `flake8` (config en `setup.cfg`). Excluye `oca_addons/` — es código de terceros vendorizado, no se reformatea. `pyrightconfig.json` (raíz) da chequeo de tipos vía el LSP de pyright, mismo criterio de exclusión.

## Despliegue a ionos

Ver skill `desplegar-ionos` para el flujo completo (sync + restart si hay `.py` + `-u` + verificación). Incluye gotchas específicos de este repo (vistas `website_id`-específicas que tapan un `-u`, escape de JSON-LD).

## ⚠️ `/commit` (slash command) — usar con cuidado en este repo

El working tree local tiene arrastre grande de cambios sin commitear preexistentes y no relacionados entre sí (ver auditorías de gobernanza en `docs/`). El comando `/commit` corre `git add`/`git status`/`git diff HEAD` sin acotar a archivos específicos — antes de usarlo acá, revisar `git status` y confirmar que solo aparecen los archivos que realmente se quieren commitear, o preferir `git add <archivos exactos>` manual (nunca `git add -A`/`.`).

## ⚠️ Proyecto duplicado

Este repo (remote `MDSODOO/COMMUNITY.git`, migración a Odoo 19 Community) tiene historial **independiente** — no comparte remote ni objetos con ninguna otra copia. Existen además:

- **`~/Documents/personal/dev-odoo/projects/medicinedepot`** — copia distinta, no relacionada por remote con esta, pero es la **activa y más completa** (30+ módulos, gestionada por el engine AURORA). Ver `~/Documents/personal/dev-odoo/CLAUDE.md`.
- `~/Documents/projects/medicine-depot` — branch `master`, sin remote.

Antes de portar cambios entre copias, confirmar en cuál se está trabajando — no asumas que son intercambiables.
