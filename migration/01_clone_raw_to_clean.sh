#!/usr/bin/env bash
# Clona medicinedepot_migration_raw -> medicinedepot_migration_clean.
#
# Idempotente: si medicinedepot_migration_clean ya existe, la borra y la
# vuelve a crear desde cero a partir de raw. NUNCA toca medicinedepot_dev
# ni medicinedepot_migration_raw (ambas se abren en modo lectura vía
# CREATE DATABASE ... TEMPLATE, que requiere que raw no tenga conexiones
# activas al momento de clonar -- por eso cerramos conexiones a raw antes).
#
# Uso: ./01_clone_raw_to_clean.sh
set -euo pipefail

DB_CONTAINER="medicinedepot_dev_db"
SRC_DB="medicinedepot_migration_raw"
DST_DB="medicinedepot_migration_clean"

echo "[1/3] Cerrando conexiones activas a $SRC_DB (necesario para poder clonarla como template)..."
docker exec -i "$DB_CONTAINER" psql -U odoo -d postgres -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE datname IN ('$SRC_DB', '$DST_DB') AND pid <> pg_backend_pid();
"

echo "[2/3] Recreando $DST_DB desde cero..."
docker exec -i "$DB_CONTAINER" psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS $DST_DB;"
docker exec -i "$DB_CONTAINER" psql -U odoo -d postgres -c "CREATE DATABASE $DST_DB TEMPLATE $SRC_DB OWNER odoo;"

echo "[3/3] Listo. Conteo de verificación:"
docker exec -i "$DB_CONTAINER" psql -U odoo -d "$DST_DB" -c "
  SELECT 'res_partner' AS tabla, COUNT(*) FROM res_partner
  UNION ALL SELECT 'stock_lot', COUNT(*) FROM stock_lot
  UNION ALL SELECT 'account_move', COUNT(*) FROM account_move;
"
