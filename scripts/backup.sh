#!/usr/bin/env bash
# backup.sh — Pull a timestamped backup of ~/.openclaw from the VPS to ./backups/
# Usage: ./scripts/backup.sh [host]
set -euo pipefail

HOST="${1:-openclaw-vps}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="./backups/${TIMESTAMP}"

echo "=== Backing up OpenClaw data from ${HOST} ==="
mkdir -p "${BACKUP_DIR}"

# Sync data directory (config, memory, skills)
rsync -avz --progress \
    -e "ssh -i ~/.ssh/openclaw_ed25519" \
    "root@${HOST}:/opt/openclaw/data/" \
    "${BACKUP_DIR}/data/"

# Sync workspace (agent working files)
rsync -avz --progress \
    -e "ssh -i ~/.ssh/openclaw_ed25519" \
    "root@${HOST}:/opt/openclaw/workspace/" \
    "${BACKUP_DIR}/workspace/"

echo ""
echo "=== Backup complete: ${BACKUP_DIR} ==="
du -sh "${BACKUP_DIR}"
