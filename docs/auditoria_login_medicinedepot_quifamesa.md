# Auditoría: personalización de `/web/login` — Medicine Depot vs Quifamesa

**Fecha:** 2026-08-17
**Alcance:** `medicinedepot_dev` (contenedor `medicinedepot_dev_odoo`) y `quifamesa_raffle_test` (contenedor `quifamesa_raffle_test_odoo`), servidor `ionos`.

## 1. Diagnóstico

### 1.1 Arquitectura de addons compartida

`quifamesa_raffle_test/docker-compose.yml` monta el `custom_addons/` completo de este repo (medicinedepot) dentro del contenedor de Quifamesa, de solo lectura, además de su propio `quifamesa_addons/`:

```yaml
volumes:
  - /opt/medicinedepot-odoo19-migration/custom_addons:/mnt/extra-addons:ro
  - /opt/quifamesa_raffle_test/quifamesa_addons:/mnt/quifamesa-addons:ro
```

Esto significa que **todos** los módulos de este repo —incluido cualquier módulo que toque `web.login`— están disponibles (instalables) en la base de datos de Quifamesa, y viceversa no aplica (Quifamesa no expone su addons al contenedor de medicinedepot), pero el problema real ocurrió en el sentido inverso: un módulo pensado para Quifamesa terminó instalado en la base de Medicine Depot.

### 1.2 Causa raíz del conflicto

Dos módulos, ambos viviendo en `custom_addons/` de este repo, heredaban `web.login` de forma independiente:

| Módulo | Templates de login | Diseño |
|---|---|---|
| `mds_raffle_campaign` (`views/login_templates.xml`) | `web_login_mds_layout`, `web_login_mds_move_form`, `web_login_mds_field_classes`, `web_login_mds_brand_accent`, `web_login_oauth_mds_divider` | Panel dividido navy (hero de la Rifa 52 Aniversario) — pensado para `quifamesa_raffle_test` |
| `medicine_depot_portal` (`views/auth_templates.xml`, `md_login_layout_override`) | `md_auth_login_ux`, `md_auth_signup_ux`, `md_login_layout_override` | Tarjeta centrada glassmorphism con CTA de registro — pensado para Medicine Depot |

**Estado real encontrado en `ir_module_module` antes del fix:**

| Módulo | `medicinedepot_dev` | `quifamesa_raffle_test` |
|---|---|---|
| `mds_raffle_campaign` | `installed` | `installed` |
| `medicine_depot_portal` | `installed` | `uninstalled` |

`mds_raffle_campaign` estaba instalado en **ambas** bases (correcto para su lógica de negocio — folios/sorteo ligados a POS/ventas), pero eso arrastraba también sus templates de login, que colisionaban con los de `medicine_depot_portal` en `medicinedepot_dev`. En `quifamesa_raffle_test` no había colisión porque `medicine_depot_portal` nunca se instaló ahí.

**Efecto verificado (antes del fix, vía `curl` a `/web/login` en `medicinedepot_dev`):** el HTML combinaba el panel `.login-wrap`/`.login-panel` de Quifamesa ("Bienvenido de vuelta") con el encabezado `.md-auth-head` de Medicine Depot ("Clientes registrados / Inicia sesión") dentro de la misma tarjeta — un híbrido visualmente roto, ninguno de los dos diseños intactos.

## 2. Solución: desacoplamiento en dos módulos independientes

| Módulo nuevo | Ubicación | Depende de | Instalado en |
|---|---|---|---|
| `md_web_login` (v19.0.1.0.0) | `medicinedepot-odoo19-migration/custom_addons/` | `web`, `website`, `auth_signup`, `medicine_depot_portal` | `medicinedepot_dev` |
| `quifamesa_web_login` (v19.0.1.0.0) | `quifamesa_raffle_test/quifamesa_addons/` (repo separado, sin remote) | `web`, `website`, `auth_signup`, `mds_raffle_campaign` | `quifamesa_raffle_test` |

Contenido movido tal cual (sin cambios funcionales) salvo el renombrado de XML ids de `quifamesa_web_login` (`mds_` → `qf_`, para que no haya colisión de identificadores si algún día ambos repos comparten addons_path de nuevo):

- `md_web_login`: `views/auth_templates.xml` (`md_auth_login_ux`, `md_auth_signup_ux`), `md_login_layout_override` (extraído de `public_templates.xml` a su propio archivo `views/login_layout_templates.xml`), `login_custom.scss`, `login_glass_island.js`.
- `quifamesa_web_login`: `views/login_templates.xml` (renombrado), la mitad login de `portal_raffle.scss` (líneas 154-503, dejando en `mds_raffle_campaign` solo el CSS de `/my/raffles` general), `login_stats.js`, `quifamesa-imagotipo-52-aniversario.png`.

`mds_raffle_campaign` queda como módulo de negocio puro (folios/sorteo/POS), sin ninguna vista que toque `web.login` — puede convivir con `medicine_depot_portal`/`md_web_login` en la misma base sin volver a colisionar.

**Por qué `quifamesa_web_login` vive en un repo/directorio distinto (y no junto a `md_web_login`):** si ambos módulos vivieran en `custom_addons/` de este repo, seguirían siendo visibles (aunque no instalados) en el addons_path del contenedor de Quifamesa vía el mismo mount `:ro` que causó el problema original — el mismo riesgo, solo que en reversa. Poniendo `quifamesa_web_login` únicamente en `/opt/quifamesa_raffle_test/quifamesa_addons/`, ni siquiera aparece en la lista de módulos instalables de `medicinedepot_dev`.

## 3. Verificación

Ejecutada vía `docker exec ... odoo -u/-i ... --stop-after-init` (dos pasos separados por módulo — ver nota técnica abajo) + `curl` a `/web/login` en ambas instancias (sin entrar credenciales, solo lectura del HTML servido):

| Chequeo | `medicinedepot_dev` (`:8069`) | `quifamesa_raffle_test` (`:8073`) |
|---|---|---|
| HTTP status | 200 | 200 |
| `oe_login_form` presente | sí (30 matches — form nativo intacto) | sí |
| Branding propio presente | "Clientes registrados" (`md-auth-head`) ✓ | "Bienvenido de vuelta" + "Portal de clientes" ✓ |
| Branding del otro proyecto presente | `login-wrap`/`login-panel`: **0** | `md-auth-head`/`md-auth-cta-panel`: **0** |
| Stats dinámicos de rifa (`login-stat-row`, query real a `raffle.campaign`) | n/a | sí, renderiza "clientes participando" / "boletos" |

Estado final en `ir_module_module`:

```
medicinedepot_dev:      mds_raffle_campaign=installed, medicine_depot_portal=installed, md_web_login=installed
quifamesa_raffle_test:  mds_raffle_campaign=installed, quifamesa_web_login=installed,
                         medicine_depot_portal=uninstalled, md_web_login=uninstalled
```

Suite de tests de `medicine_depot_portal` (`--test-tags /medicine_depot_portal`, `--workers=0`): `test_login_renders_with_form` **pasa**. 6 fallos preexistentes en `test_afiliacion_template` (3), `test_bento_dashboard_redirect.test_03_dashboard_authenticated` (1) y `test_portal_flows.TestAfiliacionEndpoint` (2) — ninguno toca `auth_templates.xml`, `login_custom.scss`, `login_glass_island.js` ni `md_login_layout_override`; quedan fuera de alcance de esta auditoría, sin relación aparente con el refactor de login.

### Nota técnica: orden de `-u`/`-i` al mover vistas entre módulos

Al mover una vista `inherit_id="web.login"` de un módulo a otro en un solo comando (`-u módulo_viejo -i módulo_nuevo`), Odoo puede intentar cargar la vista nueva **antes** de limpiar la vieja (la limpieza de `ir.model.data` huérfanos ocurre al final de todo el batch, no por módulo). Si ambas vistas comparten el mismo `priority` y el mismo xpath, la segunda falla con `cannot be located in parent view` porque el nodo ya fue consumido por la primera. Solución: separar en dos comandos — primero `-u módulo_viejo` (limpia el huérfano), después `-i módulo_nuevo`. Mismo patrón de "Odoo borra solo los registros huérfanos al correr `-u`" ya documentado en la auditoría de `md_asset_devices` (2026-08-17), aplicado aquí dos veces (una por cada par de módulos).

## 4. Riesgo residual — corregido (2026-08-17, misma sesión)

El mount `custom_addons:/mnt/extra-addons:ro` en `quifamesa_raffle_test/docker-compose.yml` exponía **los 41 módulos** de este repo (incluido `md_web_login`) como instalables desde la base de Quifamesa. Se curó a solo los dos módulos que Quifamesa realmente necesita de este repo:

```yaml
# antes:
- /opt/medicinedepot-odoo19-migration/custom_addons:/mnt/extra-addons:ro

# después:
- /opt/medicinedepot-odoo19-migration/custom_addons/mds_raffle_campaign:/mnt/extra-addons/mds_raffle_campaign:ro
- /opt/medicinedepot-odoo19-migration/custom_addons/md_product_lines:/mnt/extra-addons/md_product_lines:ro
```

`md_product_lines` es la única dependencia de `mds_raffle_campaign` que vive en `custom_addons` (sus otras dependencias — `sale`, `point_of_sale`, `mail`, `base_setup`, `portal` — son núcleo de Odoo, ya presentes en `/usr/lib/python3/dist-packages/odoo/addons`). Backup del compose original en `docker-compose.yml.bak_20260817_curated_mount` (ionos). Contenedor recreado (`docker compose down odoo && up -d odoo`; el contenedor `db` no se tocó).

**Verificado tras el cambio:** `/mnt/extra-addons` dentro del contenedor de Quifamesa ahora solo contiene `mds_raffle_campaign/` y `md_product_lines/` — `md_web_login`, `medicine_depot_portal` y el resto ya no son ni siquiera visibles/instalables desde ahí. `curl` a `/web/login` (`:8073`) → HTTP 200, panel Quifamesa intacto, sin errores en logs. `medicinedepot_dev` (`:8069`, no tocado por este cambio) → HTTP 200, sin cambios.

## 5. Hoja de ruta

- [x] Restringir el volumen compartido `custom_addons` en `quifamesa_raffle_test/docker-compose.yml` a un subconjunto curado — hecho, ver §4.
- [ ] (Fuera de alcance de esta auditoría) Investigar los 3 fallos de `test_afiliacion_template` y 1 de `test_bento_dashboard_redirect` — no relacionados al login, preexistentes.
