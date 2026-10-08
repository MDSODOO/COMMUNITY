---
name: levantar-entorno
description: Levanta, revisa logs o detiene el entorno Docker local de medicinedepot-odoo19-migration (Odoo 19 + Postgres 15). Usar cuando el usuario pida arrancar/parar el entorno de desarrollo, ver logs de Odoo, o diagnostique por qué `docker compose up` falla en este repo.
---

# Levantar el entorno local

Este repo es la copia de trabajo que se despliega en ionos vía `docker compose` (ver `CLAUDE.md`). Servicio principal: `medicinedepot_dev` (Odoo 19 Community + Postgres 15), puerto dev `8069`.

## Requisito previo — `.env.dev`

El repo NO trae `.env.dev` (está en `.gitignore`). Antes de levantar nada, verificar que exista:

```bash
test -f .env.dev || echo "FALTA .env.dev"
```

Si falta, crearlo con al menos `POSTGRES_PASSWORD` (opcionalmente `POSTGRES_DB`, `POSTGRES_USER`, `ODOO_PORT`). Sin este archivo, `docker compose up` falla o arranca con credenciales vacías — no asumir un password por defecto, preguntar al usuario si no hay pista de cuál usar.

## Comandos

```bash
docker compose --env-file .env.dev up -d        # arrancar en background
docker compose --env-file .env.dev logs -f odoo # seguir logs del servicio odoo
docker compose --env-file .env.dev down          # detener
```

## Notas

- Addons montados: `custom_addons/` completo + los 5 repos de `oca_addons/` (ver `--addons-path` en `docker-compose.yml`, no hace falta memorizarlo — leerlo ahí si se necesita el path exacto).
- `config/odoo.conf` trae `workers=5`, tuneado para el servidor real de ionos (8 CPU/15GB RAM) — no es un default liviano de dev; no "corregirlo" pensando que es un error a menos que el usuario lo pida explícitamente.
- Si el contenedor no levanta, revisar primero que el puerto `8069` no esté ya ocupado por otra instancia (`lsof -i :8069`) antes de tocar la config.
