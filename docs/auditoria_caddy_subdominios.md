# Auditoría de Caddy — Subdominios y Certificados SSL

> **Servidor:** ubuntu (74.208.191.88) — Ionos VPS
> **Reverse Proxy:** Caddy 2 (contenedor `md_caddy`)
> **Caddyfile:** `/opt/medicinedepot-odoo19-migration/caddy/Caddyfile`
> **Fecha de auditoría:** 2026-08-14
> **Validación de sintaxis:** ✅ `caddy validate` — "Valid configuration"

---

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| Subdominios declarados en Caddyfile | 3 |
| Con certificado Let's Encrypt (público) | 1 |
| Con `tls internal` (autofirmado) | 2 |
| Upstream HTTP funcional | 3/3 |
| Upstream WebSocket funcional | 1/3 |
| Hallazgos críticos | 2 |
| Hallazgos de advertencia | 2 |

---

## Matriz de Verificación de Subdominios

| # | Subdominio | Servicio / Contenedor | Puerto HTTP | Puerto WS | Estado SSL | HTTP (local) | WS (local) | DNS A Record | Notas |
|---|-----------|----------------------|------------|----------|-----------|-------------|-----------|-------------|-------|
| 1 | `odoo.bodegademedicamentos.com` | `medicinedepot_dev_odoo` | 8069 | 8072 | ✅ Let's Encrypt (CN=YE2, exp. 2026-10-18) | ✅ 200 | ✅ Funcional (gevent activo, workers=5) | ✅ 74.208.191.88 | Producción. Cert público válido. |
| 2 | **`quifamesa.bodegademedicamentos.com`** | `quifamesa_raffle_test_odoo` | 8069 | 8072 | ⚠️ `tls internal` (autofirmado) | ✅ 200 (vía --resolve) | ❌ **502** — Puerto 8072 no escucha | ❌ 174.136.25.60 | **PRIORIDAD.** Ver Hallazgos #1 y #2. |
| 3 | `n8n.bodegademedicamentos.com` | `md_n8n` | 5678 | N/A | ⚠️ `tls internal` (autofirmado) | ✅ 200 (vía --resolve) | N/A | ❌ 174.136.25.60 | Ver Hallazgo #3. |

---

## Hallazgos

### 🔴 Hallazgo #1 — CRÍTICO: DNS de Quifamesa apunta al host incorrecto

- **Subdominio:** `quifamesa.bodegademedicamentos.com`
- **Estado actual:** El registro A apunta a `174.136.25.60` (otro servidor), no a `74.208.191.88` (este servidor Ionos).
- **Impacto:** El tráfico público NO llega a este servidor. Solo funciona vía `--resolve` o acceso directo. El certificado es autofirmado (`tls internal`) como medida de protección para evitar reintentos fallidos de Let's Encrypt.
- **Acción requerida:**
  1. Cambiar el registro A de `quifamesa.bodegademedicamentos.com` a `74.208.191.88` en el panel DNS del registrador.
  2. Una vez propagado, eliminar la directiva `tls internal` del bloque de Quifamesa en el Caddyfile.
  3. Recargar Caddy: `docker exec md_caddy caddy reload --config /etc/caddy/Caddyfile`

### 🔴 Hallazgo #2 — CRÍTICO: WebSocket de Quifamesa devuelve 502 (upstream 8072 caído)

- **Subdominio:** `quifamesa.bodegademedicamentos.com`
- **Estado actual:** El contenedor `quifamesa_raffle_test_odoo` tiene `workers = 0` (modo desarrollo). Odoo en modo desarrollo NO inicia el proceso gevent en puerto 8072, por lo que las conexiones WebSocket (`/websocket`) generan `502 Bad Gateway`.
- **Impacto:** Odoo Chatter y notificaciones en tiempo real no funcionarán para Quifamesa.
- **Acción requerida:**
  1. Agregar `--workers=2 --proxy-mode` a la línea `command` del docker-compose de Quifamesa (`/opt/quifamesa_raffle_test/docker-compose.yml`).
  2. Reiniciar: `cd /opt/quifamesa_raffle_test && docker compose restart odoo`
  3. Verificar: `docker exec md_caddy curl -s http://quifamesa_raffle_test_odoo:8072/ -o /dev/null -w '%{http_code}'` → debe devolver 500 (gevent activo, rechaza GET).

### 🟡 Hallazgo #3 — ADVERTENCIA: DNS de n8n apunta al host incorrecto

- **Subdominio:** `n8n.bodegademedicamentos.com`
- **Estado actual:** Idéntico al Hallazgo #1. Registro A en `174.136.25.60`.
- **Impacto:** Solo accesible localmente o vía Tailscale.
- **Acción requerida:** Cambiar A record → `74.208.191.88`, eliminar `tls internal`, recargar.

### 🟡 Hallazgo #4 — ADVERTENCIA: Errores históricos de WebSocket en MedicineDepot

- **Subdominio:** `odoo.bodegademedicamentos.com`
- **Estado actual:** Los logs muestran errores esporádicos de `connection refused` en 8072 y un evento de `DNS server misbehaving` en fechas anteriores.
- **Impacto:** Transitorios (posiblemente durante reinicios). Actualmente funcional.
- **Acción requerida:** Solo monitorear.

---

## Detalle de Configuración del Caddyfile

### Bloque `odoo.bodegademedicamentos.com`
- `encode gzip` ✅
- Bloqueo de `/json/2/*` con `respond 403` ✅ (seguridad)
- WebSocket: `path /websocket /websocket/*` → `reverse_proxy medicinedepot_dev_odoo:8072` ✅
- Default: `reverse_proxy medicinedepot_dev_odoo:8069` ✅
- Headers de proxy: Caddy v2 los inyecta automáticamente (X-Forwarded-For, X-Forwarded-Proto, X-Forwarded-Host).

### Bloque `quifamesa.bodegademedicamentos.com` ⚠️
- `encode gzip` ✅
- `tls internal` ⚠️ (por DNS incorrecto)
- WebSocket: `path /websocket /websocket/*` → `reverse_proxy quifamesa_raffle_test_odoo:8072` ❌ (upstream caído)
- Default: `reverse_proxy quifamesa_raffle_test_odoo:8069` ✅
- Config Caddyfile correcta; el problema es el contenedor (workers=0).

### Bloque `n8n.bodegademedicamentos.com`
- `encode gzip` ✅
- `tls internal` ⚠️ (por DNS incorrecto)
- Default: `reverse_proxy md_n8n:5678` ✅

---

## Red Docker

| Contenedor | Red(es) | Resuelve desde Caddy |
|-----------|---------|---------------------|
| `md_caddy` | `medicinedepot_dev_default` | — |
| `medicinedepot_dev_odoo` | `medicinedepot_dev_default` | ✅ |
| `quifamesa_raffle_test_odoo` | `medicinedepot_dev_default` + `quifamesa_raffle_test_default` | ✅ |
| `md_n8n` | `medicinedepot_dev_default` | ✅ |
| `quifamesa_n8n` | `quifamesa_raffle_test_default` | ❌ No visible desde Caddy |

> `quifamesa_n8n` NO está en la red donde vive Caddy. Si se quiere exponer vía Caddy, hay que agregar `medicinedepot_dev_default` a su compose.

---

## Servicios sin bloque Caddy (no expuestos públicamente)

| Contenedor | Puerto Host | Descripción |
|-----------|------------|-------------|
| `quifamesa_n8n` | 127.0.0.1:5679 | n8n dedicado a Quifamesa. Solo local/Tailscale. |
| `ocr-service` | Solo red Docker | Servicio OCR interno. |
| `quifamesa_raffle_test_db` | Solo red Docker | PostgreSQL de Quifamesa. |
| `medicinedepot_dev_db` | Solo red Docker | PostgreSQL de MedicineDepot. |
| `md_n8n_db` | Solo red Docker | PostgreSQL de n8n MD. |

---

## Plan de Remediación Priorizado

| Prioridad | Acción | Complejidad | Dependencia |
|-----------|--------|------------|-------------|
| 🔴 P1 | Cambiar DNS A de `quifamesa.bodegademedicamentos.com` → `74.208.191.88` | Baja (panel DNS) | Panel registrador |
| 🔴 P1 | Habilitar `--workers=2 --proxy-mode` en Quifamesa Odoo | Media (config + restart) | Ninguna |
| 🟡 P2 | Cambiar DNS A de `n8n.bodegademedicamentos.com` → `74.208.191.88` | Baja (panel DNS) | Panel registrador |
| 🟢 P3 | Eliminar `tls internal` de ambos bloques y recargar Caddy | Baja | P1 y P2 completados |
| 🟢 P3 | Agregar headers de proxy explícitos si se requiere auditoría de IP | Baja | Opcional |

---

*Generado durante auditoría de infraestructura — 2026-08-14. Próxima revisión: post-remediación P1.*
