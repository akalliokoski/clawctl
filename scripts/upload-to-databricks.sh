#!/usr/bin/env bash
# Upload new OpenClaw session JSONL files to a Databricks Unity Catalog Volume.
# Tracks which files have already been uploaded to avoid duplicates.
#
# Usage:
#   ./upload-to-databricks.sh [session-dir] [volume-path]
#
# Designed to run as a daily cron job on the VPS (after sessions are written).
# Add to crontab with:
#   0 3 * * * /opt/openclaw/scripts/upload-to-databricks.sh \
#     >> /var/log/databricks-upload.log 2>&1
#
# Required env vars (loaded from /opt/openclaw/.env if present):
#   DATABRICKS_HOST  — https://your-workspace.azuredatabricks.net
#   DATABRICKS_TOKEN — PAT from Databricks User Settings → Access tokens

set -euo pipefail

SESSION_DIR="${1:-/opt/openclaw/data/agents/main/sessions}"
VOLUME_PATH="${2:-/Volumes/dev_catalog/openclaw_data/landing/sessions}"

# Marker directory to track uploads (survives across runs)
MARKER_DIR="/var/lib/databricks-upload"

# ---------------------------------------------------------------------------
# Load credentials from .env if not already in environment
# ---------------------------------------------------------------------------
ENV_FILE="/opt/openclaw/.env"
if [ -f "$ENV_FILE" ]; then
    # Only export the two Databricks variables from the .env file
    while IFS='=' read -r key val; do
        [[ "$key" =~ ^(DATABRICKS_HOST|DATABRICKS_TOKEN)$ ]] && export "$key=$val"
    done < <(grep -E '^(DATABRICKS_HOST|DATABRICKS_TOKEN)=' "$ENV_FILE")
fi

: "${DATABRICKS_HOST:?DATABRICKS_HOST is not set}"
: "${DATABRICKS_TOKEN:?DATABRICKS_TOKEN is not set}"

mkdir -p "$MARKER_DIR"

# ---------------------------------------------------------------------------
# Upload loop
# ---------------------------------------------------------------------------
uploaded=0
skipped=0
errors=0

shopt -s nullglob
for jsonl_file in "$SESSION_DIR"/*.jsonl; do
    filename="$(basename "$jsonl_file")"
    marker="$MARKER_DIR/${filename}.uploaded"

    if [ -f "$marker" ]; then
        skipped=$((skipped + 1))
        continue
    fi

    echo "[$(date -u +%FT%TZ)] Uploading $filename..."

    http_code=$(curl -s -o /tmp/databricks-upload-resp.txt -w "%{http_code}" \
        -X PUT \
        -H "Authorization: Bearer $DATABRICKS_TOKEN" \
        -H "Content-Type: application/octet-stream" \
        --data-binary "@$jsonl_file" \
        "${DATABRICKS_HOST}/api/2.0/fs/files${VOLUME_PATH}/${filename}")

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 201 ]; then
        touch "$marker"
        uploaded=$((uploaded + 1))
        echo "[$(date -u +%FT%TZ)] OK: $filename (HTTP $http_code)"
    else
        errors=$((errors + 1))
        resp_body="$(cat /tmp/databricks-upload-resp.txt 2>/dev/null || echo '(no response body)')"
        echo "[$(date -u +%FT%TZ)] FAILED: $filename (HTTP $http_code) — $resp_body" >&2
    fi
done

echo "[$(date -u +%FT%TZ)] Done: uploaded=$uploaded skipped=$skipped errors=$errors"

# Exit non-zero if any uploads failed (lets cron mail the error)
[ "$errors" -eq 0 ]
