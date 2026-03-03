# Databricks Integration — How It Works

## Overview

OpenClaw runs on a Hetzner VPS inside Docker. Databricks Free Edition acts as a
zero-cost analytics backend. The two are connected over plain HTTPS — no cloud
provider account, no VPN, no storage bucket required.

---

## Components

```
Hetzner VPS                          Databricks Free Edition
────────────────────                 ────────────────────────────────────
OpenClaw (Docker)                    Unity Catalog
  └─ sessions/*.jsonl   ──PUT──▶     Volume: /landing/sessions/
  └─ .env credentials               Schema: openclaw_data
                                     Catalog: dev_catalog
cron job (03:00 UTC)                        │
  upload-to-databricks.sh                   ▼
                                     DLT Pipeline (06:00 UTC)
clawctl databricks query ──GET──◀    Bronze → Silver → Gold tables
```

---

## Data flow step by step

### 1. OpenClaw writes session logs (continuous)

Every conversation turn is appended to a JSONL file on the VPS:

```
/opt/openclaw/data/agents/main/sessions/YYYY-MM-DD.jsonl
```

Each line is one JSON object — session ID, timestamp, provider, model, token
count, cost, latency, tool calls.

### 2. Cron uploads new files (03:00 UTC daily)

`scripts/upload-to-databricks.sh` runs as a cron job on the VPS. It scans the
sessions directory for `.jsonl` files that have not been uploaded yet (tracked
via marker files in `/var/lib/databricks-upload/`), and PUTs each new file to
the Databricks Files API:

```
PUT https://$DATABRICKS_HOST/api/2.0/fs/files/Volumes/dev_catalog/openclaw_data/landing/sessions/<file>
Authorization: Bearer $DATABRICKS_TOKEN
Content-Type: application/octet-stream
```

The script is idempotent — already-uploaded files are skipped on every run.

**Add to crontab on the VPS:**
```
0 3 * * * /opt/openclaw/scripts/upload-to-databricks.sh >> /var/log/databricks-upload.log 2>&1
```

### 3. DLT pipeline processes files (06:00 UTC daily)

A Databricks job triggers the medallion pipeline after the upload window:

- **Bronze** (`ingest_sessions.py`) — Auto Loader reads new JSONL files from
  the Volume using `cloudFiles` format. Schema is inferred and evolved
  automatically. Raw rows land in `dev_catalog.openclaw_data.bronze_sessions`.

- **Silver** (`build_analytics.py`) — Casts types, drops duplicates, enforces
  data quality expectations (`provider IS NOT NULL`, `tokens > 0`). Writes to
  `silver_sessions`.

- **Gold** (`build_analytics.py`) — Aggregates to daily granularity grouped by
  provider and model: session count, total tokens, total cost, average latency.
  Writes to `gold_daily_usage`.

The pipeline is defined as a Databricks Asset Bundle (`databricks-bundle/`) and
deployed once with `databricks bundle deploy`.

### 4. VPS queries results on demand

The VPS (or a local terminal) queries the Gold tables over HTTPS using the SQL
Statement Execution API:

```bash
clawctl databricks query "SELECT day, total_cost_usd FROM dev_catalog.openclaw_data.gold_daily_usage ORDER BY day DESC LIMIT 7"
```

Results are printed as a Rich table in the terminal.

---

## Low-volume alternative (no pipeline)

For inserting individual records without a file step, `clawctl databricks ingest`
batches JSONL lines into `INSERT INTO ... VALUES (...)` statements sent directly
to the SQL warehouse. The target table is created automatically on first run.
This path suits daily summaries and metrics (hundreds of rows); use the Files API
path for full session logs.

---

## Infrastructure setup (one-time)

The Unity Catalog foundation (catalog, schema, volume, grants, secret scope) is
managed with Terraform:

```bash
cd databricks-infra/
export DATABRICKS_HOST=https://your-workspace.azuredatabricks.net
export DATABRICKS_TOKEN=dapi...
terraform init
terraform apply
```

The DLT pipeline and daily job are managed with the Databricks Asset Bundle:

```bash
cd databricks-bundle/
databricks bundle deploy --target dev
```

---

## Credentials

| Where | What is stored |
|---|---|
| VPS `.env` | `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_WAREHOUSE_ID` |
| Local `.env` | Same three vars for `clawctl databricks` commands |
| Databricks secret scope `openclaw-secrets` | VPS API keys used by Databricks jobs calling back to the VPS |

`DATABRICKS_TOKEN` is a Personal Access Token generated in:
Databricks workspace → User Settings → Developer → Access tokens.

---

## clawctl commands

```
clawctl databricks ping                          # verify connection, list warehouses
clawctl databricks upload 2026-03-01.jsonl       # one-shot file upload
clawctl databricks query "SELECT ..."            # ad-hoc SQL
clawctl databricks ingest 2026-03-01.jsonl       # row-level insert (low volume)
clawctl databricks ingest --dry-run file.jsonl   # validate without writing
```
