# MedicineDepot Odoo 19 — Runbook Operativo / Operational Runbook

## 1. Contactos / Contacts
| Rol | Nombre | Contacto |
|---|---|---|
| DevOps / Sysadmin | — | — |
| Lead Developer | — | — |
| Odoo Admin | — | — |
| DB Administrator | — | — |

## 2. Topología del Sistema / System Topology
- **Servidor**: ionos (74.208.191.88), Ubuntu 24.04, 8 vCPU, 15 GB RAM, 464 GB SSD
- **Docker Engine**: 29.6.2 (Community)
- **Odoo**: 19.0-20260630 (Community)
- **PostgreSQL**: 15-alpine
- **Proxy**: Caddy 2 (TLS automático vía Let's Encrypt)
- **IA Local**: Ollama (qwen2.5vl:7b, moondream, qwen2.5-coder)
- **Dominio**: odoo.bodegademedicamentos.com

## 3. Entornos / Environments
| Entorno | Composición | Puerto | Base de Datos |
|---|---|---|---|
| dev | docker-compose.yml + .env.dev | 8069 | medicinedepot_dev |
| test | docker-compose.test.yml + .env.test | 8070 | medicinedepot_test |
| prod | — | 8071 | medicinedepot_prod (pending) |

## 4. Comandos Esenciales / Essential Commands

### Docker Compose
```bash
cd /opt/medicinedepot-odoo19-migration

# DEV
docker compose --env-file .env.dev up -d
docker compose --env-file .env.dev logs -f odoo
docker compose --env-file .env.dev restart odoo
docker compose --env-file .env.dev down --timeout 120

# TEST
docker compose -f docker-compose.test.yml --env-file .env.test up -d
docker compose -f docker-compose.test.yml --env-file .env.test logs -f odoo
```

### Backup
```bash
# Manual backup
docker exec medicinedepot_dev_db pg_dump -U odoo medicinedepot_dev > backups/manual_$(date +%Y%m%d_%H%M%S).dump
docker exec medicinedepot_dev_odoo tar czf - /var/lib/odoo/filestore/medicinedepot_dev > backups/filestore_$(date +%Y%m%d_%H%M%S).tar.gz

# Restore
cat backups/backup_20260729.dump | docker exec -i medicinedepot_dev_db psql -U odoo medicinedepot_dev
```

### Logs
```bash
# Odoo
docker compose --env-file .env.dev logs -f --tail=100 odoo

# PostgreSQL
docker compose --env-file .env.dev logs -f --tail=50 db

# Caddy (logs to stdout, filtered via journal)
docker logs md_caddy --tail 50 2>&1

# Healthcheck
/opt/medicinedepot-odoo19-migration/scripts/healthcheck.sh
```

## 5. Procedimientos de Recuperación / Recovery Procedures

### 5.1 Odoo no responde (HTTP 502/503)
1. Check health: `curl -sI http://localhost:8069`
2. Check logs: `docker compose --env-file .env.dev logs --tail=50 odoo`
3. Restart Odoo: `docker compose --env-file .env.dev restart odoo`
4. If still down, check DB: `docker compose --env-file .env.dev logs --tail=20 db`
5. Full restart: `docker compose --env-file .env.dev down && docker compose --env-file .env.dev up -d`

### 5.2 PostgreSQL caído
1. Check logs: `docker compose --env-file .env.dev logs --tail=30 db`
2. Verify disk space: `df -h`
3. Restart: `docker compose --env-file .env.dev restart db`
4. If data corrupted, restore from latest backup in backups/

### 5.3 IA (Ollama) no responde
1. Check host: `curl http://127.0.0.1:11434/api/tags`
2. Restart Ollama: `systemctl restart ollama` (or `ollama serve`)
3. Verify model loaded: `ollama list`
4. Check RAM: if vision model OOM'd, `free -h` and restart ollama service

### 5.4 Caddy / SSL failure
1. Check Caddy: `docker logs md_caddy --tail 30`
2. Caddy auto-renews Let's Encrypt certs. For manual renewal: `docker exec md_caddy caddy renew --force`
3. Verify DNS: `dig odoo.bodegademedicamentos.com`

## 6. Monitoreo / Monitoring
- Healthcheck script runs every 5 minutes via cron → `/var/log/medicinedepot-healthcheck.log`
- Backups run daily at 03:00 UTC → `backups/backup.log`
- Watchdog: `tail -f /var/log/medicinedepot-healthcheck.log`
- Odoo logs: accessible via `docker compose logs -f`

## 7. Seguridad / Security
- SSH: solo puerto 22, rate-limited (ufw)
- HTTP(S): solo puertos 80 (redirect) y 443
- Odoo: solo accesible vía Caddy reverse proxy (nunca directo por IP:puerto)
- PostgreSQL: solo accesible dentro de Docker (no expuesto al host)
- Ollama: solo en 127.0.0.1:11434 (no expuesto)
- Secretos: `.env*` y `config/*.conf` NO versionados en git

## 8. Troubleshooting Rápido / Quick Troubleshooting

### Error: "password authentication failed"
→ Las credenciales se rotaron pero DB tiene la contraseña vieja. Solución:
```bash
docker exec medicinedepot_dev_db psql -U odoo -c "ALTER USER odoo WITH PASSWORD '<nueva_password>';" postgres
docker compose --env-file .env.dev restart odoo
```

### Error: "database does not exist"
→ La base de datos no se creó automáticamente (sucede en test nuevo). Solución:
```bash
docker exec medicinedepot_test_db createdb -U odoo medicinedepot_test
```

### Error: "Ollama is busy" / "Ollama no respondió"
→ El modelo de visión está procesando otra imagen (tarda 90-240s). Esperar y reintentar. Si persiste:
```bash
curl http://127.0.0.1:11434/api/generate -d '{"model":"qwen2.5vl:7b","prompt":"ping","stream":false}' 
```

## 9. Checklist Despliegue a Producción / Production Deployment Checklist
- [ ] Rotar todas las credenciales (DB, master password, API keys)
- [ ] Verificar que `.env*` NO está en git
- [ ] Configurar UFW (solo 22, 80, 443)
- [ ] PostgreSQL: habilitar SSL (`ssl=on` en postgresql.conf)
- [ ] Odoo: `dbfilter = ^medicinedepot_prod$` + `workers = 8` (o 2*CPU+1)
- [ ] Caddy: verificar dominio y certificados
- [ ] Probar restauración desde backup
- [ ] Configurar fail2ban para /web/login
- [ ] Activar monitoreo (healthcheck + alertas)
- [ ] Agregar usuario de solo lectura para monitoreo de BD
