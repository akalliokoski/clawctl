"""Bronze layer — ingest raw OpenClaw JSONL session files from Unity Catalog Volume.

This DLT source reads JSONL files uploaded by the VPS via the Files API using
Auto Loader (cloudFiles). New files are detected automatically on each pipeline run.
Schema is inferred and evolved automatically.

Volume upload path: /Volumes/dev_catalog/openclaw_data/landing/sessions/
Upload command:     clawctl databricks upload <file.jsonl>
"""

import dlt
from pyspark.sql.functions import col, current_timestamp, input_file_name

# Injected by DAB from databricks.yml pipeline configuration
_CATALOG = spark.conf.get("catalog", "dev_catalog")  # type: ignore[name-defined]  # noqa: F821
_SCHEMA = spark.conf.get("schema", "openclaw_data")  # type: ignore[name-defined]  # noqa: F821

_SESSIONS_VOLUME = f"/Volumes/{_CATALOG}/{_SCHEMA}/landing/sessions/"
_SCHEMA_LOCATION = f"/Volumes/{_CATALOG}/{_SCHEMA}/_schema/sessions"


@dlt.table(
    name="bronze_sessions",
    comment="Raw OpenClaw session JSONL files — one row per conversation event",
    table_properties={"quality": "bronze"},
)
@dlt.expect("session_id_present", "session_id IS NOT NULL")
def bronze_sessions():  # type: ignore[return]
    """Stream new JSONL files from the landing Volume into a Delta table."""
    return (
        spark.readStream.format("cloudFiles")  # type: ignore[name-defined]  # noqa: F821
        .option("cloudFiles.format", "json")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
        .option("cloudFiles.schemaLocation", _SCHEMA_LOCATION)
        .load(_SESSIONS_VOLUME)
        .withColumn("_source_file", input_file_name())
        .withColumn("_ingested_at", current_timestamp())
    )
