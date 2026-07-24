#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/opt/medicinedepot-odoo19-migration"
BACKUP_DIR="$PROJECT_DIR/backups"
LOG_FILE="$BACKUP_DIR/backup.log"
RETENTION_DAYS=14
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

cd "$PROJECT_DIR"
mkdir -p "$BACKUP_DIR"

log() {
    echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') | $1" >> "$LOG_FILE"
}

log "Iniciando backup"

DUMP_FILE="$BACKUP_DIR/medicinedepot_dev_${TIMESTAMP}.dump"
if docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "$DUMP_FILE" 2>>"$LOG_FILE"; then
    log "Dump de base de datos OK: $DUMP_FILE ($(du -h "$DUMP_FILE" | cut -f1))"
else
    log "ERROR: pg_dump falló"
    rm -f "$DUMP_FILE"
    exit 1
fi

FILESTORE_FILE="$BACKUP_DIR/medicinedepot_dev_filestore_${TIMESTAMP}.tar.gz"
if docker run --rm \
    -v medicinedepot_dev_medicinedepot_dev_odoo_data:/data:ro \
    -v "$BACKUP_DIR":/backup \
    alpine:3 \
    tar czf "/backup/$(basename "$FILESTORE_FILE")" -C /data . >>"$LOG_FILE" 2>&1; then
    log "Filestore OK: $FILESTORE_FILE ($(du -h "$FILESTORE_FILE" | cut -f1))"
else
    log "ERROR: backup de filestore falló"
fi

DELETED=$(find "$BACKUP_DIR" -maxdepth 1 -name "medicinedepot_dev_*" -mtime "+${RETENTION_DAYS}" -print -delete | wc -l)
log "Retención: $DELETED archivo(s) de más de ${RETENTION_DAYS} días eliminados"

log "Backup completado"
