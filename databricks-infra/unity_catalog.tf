# ---------------------------------------------------------------------------
# Unity Catalog — catalog, schema, and landing Volume
# ---------------------------------------------------------------------------
# The landing Volume is where the VPS uploads JSONL files via the Files API.
# A DLT pipeline (in databricks-bundle/) then reads from here via Auto Loader.

resource "databricks_catalog" "dev" {
  name    = var.catalog_name
  comment = "Personal development catalog for OpenClaw analytics"
}

resource "databricks_schema" "openclaw" {
  catalog_name = databricks_catalog.dev.name
  name         = "openclaw_data"
  comment      = "OpenClaw ingested data — sessions, metrics, memory"
}

# Landing zone: VPS uploads JSONL files here via the Files API.
# DLT Auto Loader reads from /Volumes/<catalog>/openclaw_data/landing/sessions/
resource "databricks_volume" "landing" {
  catalog_name = databricks_catalog.dev.name
  schema_name  = databricks_schema.openclaw.name
  name         = "landing"
  volume_type  = "MANAGED"
  comment      = "Receives JSONL uploads from VPS via Files API"
}

# Grant the current user full access to the catalog and schema
resource "databricks_grants" "dev_catalog" {
  catalog = databricks_catalog.dev.name
  grant {
    principal  = data.databricks_current_user.me.user_name
    privileges = ["USE_CATALOG", "CREATE_SCHEMA"]
  }
}

resource "databricks_grants" "openclaw_schema" {
  schema = "${databricks_catalog.dev.name}.${databricks_schema.openclaw.name}"
  grant {
    principal  = data.databricks_current_user.me.user_name
    privileges = [
      "USE_SCHEMA",
      "CREATE_TABLE",
      "CREATE_VOLUME",
      "READ_VOLUME",
      "WRITE_VOLUME",
    ]
  }
}
