# Databricks on a shoestring: the complete personal-use guide

**You can run a meaningful Databricks environment for $0/month.** Databricks Free Edition, launched June 2025, replaced the old Community Edition and includes Unity Catalog, MLflow, Delta Live Tables, SQL warehouses, and model serving — all serverless, no credit card required, no cloud provider account needed. For a personal AI assistant like OpenClaw running on a VPS, this creates a powerful data engineering and AI governance learning platform at zero cost. This guide covers everything needed to connect OpenClaw to Databricks entirely within Free Edition.

---

## What OpenClaw is and why Databricks fits

OpenClaw (formerly Clawdbot/Moltbot) is a free, open-source, self-hosted personal AI assistant platform with **196k+ GitHub stars**. Built in TypeScript, it runs as a single-process gateway that connects LLMs (Claude, GPT, DeepSeek) to 12+ messaging platforms including WhatsApp, Telegram, Slack, Discord, and Signal. It supports persistent memory via hybrid BM25 + vector search over SQLite, tool execution (bash, browser automation), cron jobs, webhooks, and an extensible plugin system with MCP support.

OpenClaw produces rich, structured data streams that are ideal for Databricks ingestion. **Conversation session logs** live in `~/.openclaw/agents/<agentId>/sessions/*.jsonl` as full transcripts with tool calls and timestamps. **Model usage data** captures provider, token counts, cost per call, latency, and cache hits. **Tool call analytics** record tool name, inputs/outputs, success/failure, and duration. **Memory indexes** in SQLite contain text chunks with embeddings, and **markdown memory files** hold curated long-term knowledge. Gateway logs provide operational metrics across all channels.

### Ingestion without cloud storage

OpenClaw data is pushed directly into Databricks using two native APIs — no cloud provider account, no storage bucket required:

**Option A — Databricks Files API (recommended).** Unity Catalog Volumes are a managed file store built into every workspace, accessible via the Files REST API (`PUT /api/2.0/fs/files/{volume-path}`). A cron job on the VPS uploads new JSONL session files and SQLite CSV dumps directly to a Volume. A DLT pipeline then reads from `/Volumes/dev_catalog/openclaw_data/landing/` using Auto Loader — the pipeline logic is identical to what you'd write for any file source.

```bash
# Example: upload today's session file from VPS cron
curl -X PUT \
  -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @~/.openclaw/agents/default/sessions/2025-06-15.jsonl \
  "https://$DATABRICKS_HOST/api/2.0/fs/files/Volumes/dev_catalog/openclaw_data/landing/sessions/2025-06-15.jsonl"
```

**Option B — SQL Statement Execution API (simplest).** For smaller data volumes, skip files entirely and insert rows directly into Delta tables via `POST /api/2.0/sql/statements/`. The VPS script reads JSONL lines and batches them into multi-row INSERT statements. No intermediate file step, no pipeline needed for basic ingestion. Suitable for daily summaries and metrics where row counts are in the hundreds rather than millions.

```bash
# Example: insert a usage record directly
curl -X POST \
  -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "warehouse_id": "<your-warehouse-id>",
    "statement": "INSERT INTO dev_catalog.openclaw_data.usage VALUES (:ts, :provider, :tokens, :cost)",
    "parameters": [
      {"name": "ts", "value": "2025-06-15T14:23:00Z", "type": "TIMESTAMP"},
      {"name": "provider", "value": "anthropic", "type": "STRING"},
      {"name": "tokens", "value": "1842", "type": "INT"},
      {"name": "cost", "value": "0.0092", "type": "DOUBLE"}
    ]
  }' \
  "https://$DATABRICKS_HOST/api/2.0/sql/statements/"
```

The existing PostgreSQL persistence plugin (PR #19462) provides a template for a custom TypeScript plugin — swap Postgres for the SQL Statement Execution API to stream data in near-real-time via OpenClaw's `before_agent_start` and `agent_end` lifecycle events.

---

## Free Edition capabilities

**Databricks Community Edition was retired January 1, 2026.** Its replacement, Free Edition, is dramatically more capable. Available at signup.databricks.com with no credit card and no cloud provider account, it provides a serverless-only, quota-limited environment that covers the core learning needs for data engineering and AI governance.

Free Edition includes:

- **Unity Catalog** — governance, metastore, column-level lineage
- **MLflow** — experiment tracking, model registry
- **Jobs** — up to 5 concurrent tasks
- **Delta Live Tables** — 1 active pipeline
- **2X-Small SQL warehouse** — for ad-hoc queries and dashboards
- **Genie** — natural-language dashboard queries
- **Model serving endpoints** (no GPU)
- **Vector search** — 1 endpoint
- **Unity Catalog Volumes** — managed file storage, no external account needed
- **Files API** — programmatic file uploads from your VPS
- **Databricks Assistant** — AI copilot in the UI

Daily compute quotas exist but **99%+ of users never hit them**. The environment runs entirely on Databricks-managed serverless compute — no cluster configuration, no VM sizing, no idle costs.

What's missing: R and Scala languages, custom compute configurations, GPUs, online tables, account-level APIs, SSO/SCIM, private networking, and commercial use rights. For a personal learning project, none of these are blockers. **Free Edition is sufficient for approximately 80-90% of data engineering and AI governance learning objectives.**

---

## What costs nothing on Free Edition

Everything in this guide runs at **$0**:

| Resource | Free Edition status |
|---|---|
| Unity Catalog Volumes (landing zone) | Included, Databricks-managed |
| Files API uploads | Included |
| SQL Statement Execution API | Included (uses SQL warehouse quota) |
| Delta Live Tables pipeline | 1 active pipeline included |
| MLflow experiment tracking | Included |
| SQL warehouse (2X-Small) | Included, auto-stops when idle |
| Unity Catalog governance | Included |
| Model serving (CPU) | Included |

The only thing that costs money is your existing VPS, which you already have running OpenClaw. Databricks itself is free.

---

## Six use cases connecting OpenClaw to Databricks

### Monitoring through ingested Delta tables

Databricks Lakehouse Monitoring (now called Data Profiling) does not directly monitor external applications. Instead, the pattern is: ingest OpenClaw's logs and metrics into Delta tables, then create monitors on those tables. The monitoring engine supports three profile types — **Time Series** (compare distributions over time windows), **Snapshot** (monitor full table state), and **Inference** (model quality metrics including toxicity and drift). You define data quality expectations, set alert thresholds on null rates or distribution shifts, and get auto-generated dashboards.

For OpenClaw, create a medallion architecture: Bronze tables hold raw JSONL session logs and gateway metrics uploaded to a Unity Catalog Volume and ingested via DLT. Silver tables parse and structure conversations, deduplicate events, and validate schemas. Gold tables aggregate daily usage stats, error rates, latency percentiles, and cost summaries. Monitoring runs on serverless compute — all included in Free Edition.

### AI governance with Unity Catalog and MLflow

Unity Catalog provides comprehensive governance for all data and AI assets. Models register as `catalog.schema.model_name` with full versioning, aliases (champion/challenger), and cross-workspace sharing. **Column-level data lineage** is captured automatically across queries, and when you log training data via `mlflow.log_input()`, lineage traces from source tables through to model versions.

From your VPS, configure the MLflow Python client with `DATABRICKS_HOST` and `DATABRICKS_TOKEN` environment variables to log experiments remotely. Every experiment run, parameter set, metric, and artifact is tracked in the Databricks-hosted MLflow instance, governed by Unity Catalog permissions. Audit logging records all access to data and AI assets in queryable system tables. Fine-grained ANSI SQL-based permissions (GRANT/REVOKE) control who can create models, read data, or manage schemas.

### Data pipelines with Delta Live Tables

Delta Live Tables (rebranded as Spark Declarative Pipelines under the Lakeflow umbrella, June 2025) provides declarative ETL where you define transformations in SQL or Python and the system handles orchestration, dependency management, and error recovery. Three dataset types exist: **Streaming Tables** (exactly-once incremental processing), **Materialized Views** (recomputed as needed), and **Views** (logical). Built-in `EXPECT` clauses enforce data quality rules — e.g., `EXPECT (session_id IS NOT NULL)` — with configurable behavior for violations (drop, flag, or fail).

A DLT pipeline reads uploaded JSONL files directly from a Unity Catalog Volume:

```python
import dlt
from pyspark.sql.functions import col

@dlt.table(name="bronze_sessions", comment="Raw session logs from OpenClaw")
def bronze_sessions():
    return (
        spark.readStream.format("cloudFiles")
            .option("cloudFiles.format", "json")
            .option("cloudFiles.schemaLocation", "/Volumes/dev_catalog/openclaw_data/_schema")
            .load("/Volumes/dev_catalog/openclaw_data/landing/sessions/")
    )
```

Free Edition allows 1 active pipeline — sufficient for a personal project. Schedule it to run daily via Databricks Workflows to stay within quota.

### Secrets management: use Databricks for Databricks, not for your VPS

**Databricks secrets are not designed as an external secrets vault.** The critical limitation: `dbutils.secrets.get()` only works inside Databricks compute. There is no REST API endpoint to retrieve secret values from an external application. Secrets are workspace-scoped, limited to 100 scopes with 1,000 secrets each, and lack automatic rotation.

The correct architecture: use Databricks secret scopes to store credentials that Databricks jobs need to connect to your VPS (API keys, database passwords). For OpenClaw's own secrets, use a dedicated secrets manager — HashiCorp Vault, Infisical, or a simple encrypted file on the VPS. **The flow is one-directional**: Databricks reads its secrets to connect outward, not the other way around.

### Serving data back to OpenClaw

The **SQL Statement Execution API** (`POST /api/2.0/sql/statements/`) is the most practical integration point. Your VPS sends HTTPS requests to execute SQL queries against the Databricks SQL warehouse, receives results in JSON, CSV, or Arrow format. No driver installation needed — pure REST. Authentication uses a Personal Access Token or OAuth M2M service principal credentials.

For ML predictions, **Model Serving endpoints** provide REST APIs with scale-to-zero capability (no idle cost, included in Free Edition). **Delta Sharing** enables read-only data access from any platform via an open protocol — your VPS can use the `delta-sharing` Python library to read shared tables. For bidirectional integration, Unity Catalog's HTTP connections feature lets Databricks call your VPS's API directly from SQL using the `http_request()` function.

### Network connectivity is straightforward

All Databricks APIs are HTTPS-secured over the public internet. No VPN or private link is needed — standard REST calls work from any VPS. Authentication via **OAuth M2M** (service principal with client_id/client_secret generating short-lived tokens) is recommended over long-lived Personal Access Tokens. Set `DATABRICKS_HOST` and credential environment variables on your VPS.

---

## Infrastructure as Code: the split-stack approach

### Terraform is the primary tool

The Databricks Terraform provider (`databricks/databricks`, **v1.110+**) is the most mature IaC option with **10 million+ installations** and full GA status. It covers virtually every Databricks resource: clusters, cluster policies, jobs, Unity Catalog (metastore, catalogs, schemas, tables, volumes, grants), SQL warehouses, secret scopes, permissions, model serving, vector search, and identity management. Authentication via PAT or OAuth M2M.

**OpenTofu is compatible** but not officially tested. The Databricks provider is listed on the OpenTofu registry, and identical `.tf` files work with both `terraform` and `tofu` CLI commands. For a personal project where Terraform's BSL license is a concern, OpenTofu is a viable drop-in replacement.

On Free Edition, Terraform manages resources *within* your workspace — the workspace itself is provisioned by Databricks at signup and already exists. There is no workspace infrastructure to manage.

### Databricks Asset Bundles handle workloads

Databricks Asset Bundles (DABs) complement Terraform by managing application-layer resources — jobs, pipelines, notebooks, ML experiments, model serving endpoints, dashboards. Defined in YAML (`databricks.yml`), they package source code with resource definitions and deploy via the Databricks CLI (`databricks bundle deploy`). DABs use Terraform under the hood but abstract away state files and provider management.

The recommended **split-stack strategy**:

| Layer | Tool | What it manages |
|---|---|---|
| Infrastructure foundation | Terraform/OpenTofu | Unity Catalog objects, Volumes, secret scopes, SQL warehouse config, permissions |
| Application workloads | DABs | Jobs, DLT pipelines, notebooks, ML experiments, model serving, dashboards |

### Minimal Terraform configuration

Keep the project flat — a single directory with a few `.tf` files is ideal for a solo developer:

```
databricks-infra/
├── main.tf              # Provider config, data sources
├── unity_catalog.tf     # Catalog, schema, volumes, grants
├── secrets.tf           # Secret scopes
├── variables.tf         # Input variables
├── outputs.tf           # Workspace URL, warehouse IDs
├── .terraform.lock.hcl  # Lock file (commit to git)
└── .gitignore           # Ignore .terraform/, *.tfstate, *.tfvars
```

```hcl
terraform {
  required_version = ">= 1.1.5"
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.110"
    }
  }
}

provider "databricks" {}  # Uses DATABRICKS_HOST + DATABRICKS_TOKEN env vars

data "databricks_current_user" "me" {}

resource "databricks_secret_scope" "main" { name = "openclaw-secrets" }

resource "databricks_catalog" "dev" {
  name    = "dev_catalog"
  comment = "Personal development catalog"
}

resource "databricks_schema" "openclaw" {
  catalog_name = databricks_catalog.dev.name
  name         = "openclaw_data"
  comment      = "OpenClaw ingested data"
}

# Landing zone Volume — VPS uploads files here via Files API
resource "databricks_volume" "landing" {
  catalog_name = databricks_catalog.dev.name
  schema_name  = databricks_schema.openclaw.name
  name         = "landing"
  volume_type  = "MANAGED"
  comment      = "Receives JSONL uploads from VPS via Files API"
}
```

Complement this with a DAB for workloads:

```yaml
# databricks.yml
bundle:
  name: openclaw-pipelines
  databricks_cli_version: ">= 0.218.0"
workspace:
  host: ${var.DATABRICKS_HOST}
resources:
  jobs:
    daily_etl:
      name: "OpenClaw Daily ETL"
      schedule:
        quartz_cron_expression: "0 0 6 * * ?"
        timezone_id: "UTC"
      tasks:
        - task_key: ingest_sessions
          notebook_task:
            notebook_path: ./src/ingest_sessions.py
        - task_key: build_analytics
          depends_on: [{ task_key: ingest_sessions }]
          notebook_task:
            notebook_path: ./src/build_analytics.py
targets:
  dev:
    default: true
    mode: development
```

Pin provider versions with `~>` for minor flexibility, commit `.terraform.lock.hcl` to git, use environment variables for authentication, and always run `terraform plan` before `apply`.

---

## Recommended minimal architecture

The architecture connects two layers — your VPS running OpenClaw and the Databricks workspace — with no cloud provider or storage account in between.

```
┌──────────────────────┐   Files API (PUT)   ┌─────────────────────────┐
│   VPS (OpenClaw)     │ ──── upload JSONL ──▶│   Databricks            │
│                      │                      │                         │
│  Sessions (JSONL)    │                      │  UC Volume: /landing/   │
│  Memory (SQLite)     │ ◀── query results ───│       │                 │
│  Gateway Logs        │   SQL Statement API  │       ▼ DLT pipeline    │
└──────────────────────┘                      │  Bronze: raw logs       │
                                              │  Silver: parsed         │
         OR                                   │  Gold: analytics        │
                                              │                         │
┌──────────────────────┐  SQL Statement API   │  Unity Catalog          │
│   VPS (OpenClaw)     │ ──── INSERT rows ───▶│  MLflow Tracking        │
│  (low-volume path)   │                      │  SQL Warehouse          │
└──────────────────────┘                      │  Model Serving          │
                                              └─────────────────────────┘
```

**Data flows inward** via one of two paths. For file-based ingestion, a cron job on the VPS uploads JSONL session files to the Unity Catalog Volume via the Files API. A DLT pipeline reads from that Volume path and processes files through the medallion architecture. For row-based ingestion (simpler, lower volume), the VPS inserts records directly into Delta tables via the SQL Statement Execution API — no file step needed.

**Data flows outward** via the SQL Statement Execution API — the VPS queries analytics tables or calls model serving endpoints over plain HTTPS.

**Authentication** uses an OAuth M2M service principal for VPS-to-Databricks communication. Store the service principal credentials in your VPS's own secrets manager. Databricks secret scopes hold any VPS credentials that Databricks jobs need for outbound calls.

---

## Conclusion

Free Edition makes the entire setup described in this guide possible at zero cost, with no cloud provider account required at any point. Unity Catalog Volumes replace any need for an external storage bucket — files upload directly from your VPS via the Files REST API, Auto Loader reads from Volume paths, and Databricks manages all underlying storage. The SQL Statement Execution API handles both ingestion (inserts) and retrieval (queries) over plain HTTPS from any VPS.
