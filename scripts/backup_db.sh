#!/usr/bin/env bash
set -e

BACKUP_DIR="${BACKUP_DIR:-$HOME/submittery_backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="submittery_backup_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[*] Creating database dump: ${BACKUP_DIR}/${FILENAME}..."
docker exec submittery_db pg_dump -U postgres submittery | gzip > "${BACKUP_DIR}/${FILENAME}"

echo "[+] Database backup created successfully (${FILENAME})."

# Keep last 14 days of backups
echo "[*] Pruning backups older than 14 days..."
find "$BACKUP_DIR" -type f -name "submittery_backup_*.sql.gz" -mtime +14 -exec rm {} \;
echo "[+] Done."
