#!/bin/bash
# Healthcheck script for MedicineDepot Odoo
# Runs as a cron job every 5 minutes (/etc/cron.d/medicinedepot-healthcheck)
#
# Notificaciones: grupo de Telegram del proyecto.
#   - Credenciales en /etc/medicinedepot/alerts.env (fuera del repo, chmod 600).
#   - Solo avisa en CAMBIO de estado (OK->FALLO y FALLO->RECUPERADO), no en cada
#     ciclo: con 5 min de intervalo, una caída de 3 h serían 36 mensajes iguales
#     y el grupo acabaría silenciado.
#   - Si algo sigue caído, recuerda una vez por hora (REPEAT_AFTER_CYCLES).

set -euo pipefail

ALERTS_ENV="/etc/medicinedepot/alerts.env"
STATE_DIR="/var/lib/medicinedepot-healthcheck"
REPEAT_AFTER_CYCLES=12          # recordatorio cada 13 ciclos x 5 min ≈ 65 min
OLLAMA_URL="http://100.84.63.23:11434/api/version"   # mds_agent1 via Tailscale

TELEGRAM_BOT_TOKEN=""
TELEGRAM_CHAT_ID=""
if [ -r "$ALERTS_ENV" ]; then
    # shellcheck source=/dev/null
    . "$ALERTS_ENV"
fi

mkdir -p "$STATE_DIR"

HOST="$(hostname)"
NOW="$(date -u '+%Y-%m-%d %H:%M UTC')"

send_telegram() {
    local text="$1"
    [ -z "${TELEGRAM_BOT_TOKEN:-}" ] && return 0
    [ -z "${TELEGRAM_CHAT_ID:-}" ] && return 0
    curl -s --max-time 15 \
        -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "parse_mode=HTML" \
        -d "disable_web_page_preview=true" \
        --data-urlencode "text=${text}" >/dev/null 2>&1 || true
}

# report_state <clave> <ok|fail> <descripcion>
report_state() {
    local key="$1" status="$2" detail="$3"
    local state_file="$STATE_DIR/${key//[^a-zA-Z0-9_-]/_}"
    local prev="OK" count=0

    if [ -r "$state_file" ]; then
        read -r prev count < "$state_file" 2>/dev/null || { prev="OK"; count=0; }
    fi
    prev="${prev:-OK}"
    count="${count:-0}"

    if [ "$status" = "fail" ]; then
        if [ "$prev" != "FAIL" ]; then
            send_telegram "🔴 <b>FALLO</b> — ${detail}
<i>${HOST} · ${NOW}</i>"
            printf 'FAIL 0\n' > "$state_file"
        elif [ "$count" -ge "$REPEAT_AFTER_CYCLES" ]; then
            send_telegram "🔴 <b>SIGUE CAÍDO</b> — ${detail}
<i>${HOST} · ${NOW}</i>"
            printf 'FAIL 0\n' > "$state_file"
        else
            printf 'FAIL %s\n' "$((count + 1))" > "$state_file"
        fi
    else
        if [ "$prev" = "FAIL" ]; then
            send_telegram "✅ <b>RECUPERADO</b> — ${detail}
<i>${HOST} · ${NOW}</i>"
        fi
        printf 'OK 0\n' > "$state_file"
    fi
}

# check_endpoint <nombre> <url> [timeout] [codigos_ok]
# codigos_ok: lista separada por espacios. Por defecto "200".
check_endpoint() {
    local name="$1" url="$2" timeout="${3:-10}" ok_codes="${4:-200}"
    local status code matched=0
    status=$(curl -so /dev/null -w "%{http_code}" --max-time "$timeout" "$url" 2>/dev/null || echo "000")
    for code in $ok_codes; do
        [ "$status" = "$code" ] && matched=1 && break
    done
    if [ "$matched" -eq 0 ]; then
        echo "[ALERT] $name returned HTTP $status"
        report_state "endpoint_$name" fail "$name responde HTTP ${status}"
    else
        echo "[OK] $name — HTTP $status"
        report_state "endpoint_$name" ok "$name"
    fi
}

echo "=== Healthcheck $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="
check_endpoint "Odoo Dev" "http://localhost:8069/web/health"
check_endpoint "Odoo Test" "http://localhost:8070/web/health"
# Caddy en :80 responde 308 (redirige a HTTPS) — ESO ES LO SANO. El script
# anterior exigia 200 y por eso llevaba 623 falsas alarmas en el log, una cada
# 5 min desde que se instalo, sin que nadie las viera.
check_endpoint "Caddy" "http://localhost:80/" 10 "200 308"
# El camino real del usuario: valida Caddy + certificado TLS + ruteo + Odoo
# de una sola vez. Si el cert no renueva, esto lo caza.
check_endpoint "Sitio público (HTTPS)" "https://odoo.bodegademedicamentos.com/web/health" 20
# IA local: sin esto, una caída de Ollama pasa inadvertida hasta que alguien
# reporta que "ya no lee las fotos" (paso exactamente eso el 2026-07-31).
check_endpoint "Ollama (IA local)" "$OLLAMA_URL" 15

# Check Docker containers
for container in medicinedepot_dev_odoo medicinedepot_dev_db medicinedepot_test_odoo medicinedepot_test_db md_caddy; do
    status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "missing")
    if [ "$status" != "running" ]; then
        echo "[ALERT] Container $container is $status"
        report_state "container_$container" fail "Contenedor <code>${container}</code> está en estado <b>${status}</b>"
    else
        echo "[OK] Container $container is running"
        report_state "container_$container" ok "Contenedor <code>${container}</code>"
    fi
done

# Check disk usage
disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$disk_usage" -gt 85 ]; then
    echo "[ALERT] Disk usage at ${disk_usage}%"
    report_state "disk" fail "Disco al <b>${disk_usage}%</b>"
else
    report_state "disk" ok "Disco (${disk_usage}%)"
fi

# Check memory
mem_total=$(free -m | awk '/^Mem:/{print $2}')
mem_avail=$(free -m | awk '/^Mem:/{print $7}')
mem_pct=$(( (mem_total - mem_avail) * 100 / mem_total ))
if [ "$mem_pct" -gt 85 ]; then
    echo "[ALERT] Memory usage at ${mem_pct}%"
    report_state "memory" fail "Memoria al <b>${mem_pct}%</b>"
else
    report_state "memory" ok "Memoria (${mem_pct}%)"
fi

echo "=== Healthcheck complete ==="
