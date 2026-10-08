---
name: desplegar-ionos
description: Despliega cambios de custom_addons/ (Python o XML) al servidor ionos y los aplica en una base de datos Odoo (medicinedepot_dev u otra). Usar cuando el usuario pida sincronizar/desplegar/subir cambios a ionos, actualizar un módulo, o cuando algo editado localmente no se refleja en el sitio en vivo.
---

# Desplegar cambios a ionos

Patrón repetible usado en este proyecto para llevar un cambio de `custom_addons/` (local) al servidor `ionos` y que quede activo en una base de datos real. Server accesible vía `ssh ionos`.

## 1. Validar antes de sincronizar

```bash
python3 -m py_compile <archivo>.py                                  # .py
python3 -c "import xml.dom.minidom as m; m.parse('<archivo>.xml')"  # .xml
```

Un XML mal formado o un .py con SyntaxError rompe el `-u` a mitad de un batch — más caro de diagnosticar después que antes.

## 2. Sincronizar (rsync, no scp suelto)

```bash
rsync -av custom_addons/<modulo>/<ruta>/<archivo> ionos:/opt/medicinedepot-odoo19-migration/custom_addons/<modulo>/<ruta>/<archivo>
```

Cuidado: si se pasan varios archivos de módulos/carpetas distintas en un solo `rsync origen1 origen2 ... destino`, TODOS terminan en el último `destino` literal (no cada uno en su ruta real) — sincronizar cada archivo con su propio destino, o un directorio a la vez. (Ver `docs/auditoria_seo_medicine_depot.md` para el incidente real de esto.)

## 3. Restart si tocaste `.py`

Cambios a modelos/controladores Python **requieren** `docker restart` — `-u` solo no basta para que el proceso vivo recargue el código (ver memoria `project_odoo_python_requiere_restart`):

```bash
ssh ionos "cd /opt/medicinedepot-odoo19-migration && docker compose --env-file .env.dev restart odoo"
sleep 8
ssh ionos "docker exec medicinedepot_dev_odoo curl -s -o /dev/null -w 'boot=%{http_code}\n' http://localhost:8069/web/login"
```

## 4. Actualizar el/los módulo(s) (`-u`)

Usar `--no-http` para no chocar con el puerto del proceso ya corriendo:

```bash
ssh ionos '
source /opt/medicinedepot-odoo19-migration/.env.dev
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" medicinedepot_dev_odoo \
  odoo -u <modulo1>,<modulo2> \
  --db_host=medicinedepot_dev_db --db_port=5432 --db_user=odoo --db_password="$POSTGRES_PASSWORD" \
  -d medicinedepot_dev \
  --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons,/mnt/oca-account-financial-tools,/mnt/oca-account-reconcile,/mnt/oca-account-financial-reporting,/mnt/oca-reporting-engine,/mnt/oca-server-ux \
  --stop-after-init --no-http --log-level=warn
'
```

Revisar el output por `ParseError` / `could not be located in parent view` (típico al mover una vista `inherit_id` de un módulo a otro en un solo `-u` — solución: separar en dos comandos, `-u modulo_viejo` primero, `-i modulo_nuevo` después).

## 5. Restart final + verificación

```bash
ssh ionos "cd /opt/medicinedepot-odoo19-migration && docker compose --env-file .env.dev restart odoo"
sleep 8
curl -s -o /dev/null -w "%{http_code}\n" https://odoo.bodegademedicamentos.com/en
```

## Gotchas conocidos de este proyecto

- **Vistas "específicas de sitio" (`website_id` no nulo) tapan el cambio genérico.** Si tras `-u` + restart el HTML no refleja el cambio, verificar `select id, website_id from ir_ui_view where key = '<modulo>.<template_id>'` — si hay más de una fila, la de `website_id` no nulo gana en runtime y no la actualiza un `-u` normal.
- **JSON-LD u otro contenido "ya escapado" generado en Python**: envolver en `markupsafe.Markup(...)` antes de un `t-out`, si no las comillas salen como `&#34;` (JSON inválido).
- Cambios a archivos `noupdate="1"` en registros YA existentes se ignoran en `-u` — si hace falta forzar, borrar la fila de `ir_model_data` correspondiente primero.
- Ver `docs/auditoria_seo_medicine_depot.md` y memoria `project_auditoria_seo_medicine_depot_2026-08-17` para el detalle completo de estos dos últimos puntos.

## Commit (sin push)

Comitear localmente Y en el repo de ionos (son commits independientes, historiales separados salvo que ionos tenga el mismo remote):

```bash
git add <archivos exactos, nunca -A>
git commit -m "..."
ssh ionos "cd /opt/medicinedepot-odoo19-migration && git add <mismos archivos> && git commit -m '...'"
```

Push solo con confirmación explícita del usuario.
