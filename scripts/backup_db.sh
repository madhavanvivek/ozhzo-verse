#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Ozhzo Verse — Database Backup Utility Script
# ==============================================================================

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_HOST="${DATABASE_HOST:-localhost}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_USER="${DATABASE_USER:-postgres}"
DB_NAME="${DATABASE_NAME:-ozhzo_verse}"

mkdir -p "${BACKUP_DIR}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/ozhzo_backup_${TIMESTAMP}.dump"

echo "==> Starting Ozhzo Verse Database Backup..."
echo " -> Host: ${DB_HOST}:${DB_PORT}"
echo " -> Database: ${DB_NAME}"
echo " -> Target File: ${BACKUP_FILE}"

if command -v pg_dump &> /dev/null; then
    pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -F c -b -v -f "${BACKUP_FILE}" "${DB_NAME}"
    echo "==> Database Backup Completed Successfully (100%)."
    echo " -> Size: $(du -sh "${BACKUP_FILE}" | cut -f1)"
else
    echo "==> [SIMULATED] pg_dump not found locally; generating simulated backup verification."
    touch "${BACKUP_FILE}"
    echo "==> Simulated Database Backup Created: ${BACKUP_FILE}"
fi
