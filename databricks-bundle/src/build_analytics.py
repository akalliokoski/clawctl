"""Silver + Gold layers — parse, validate, and aggregate OpenClaw session data.

Silver: parsed, validated, deduplicated events (one row per conversation turn).
Gold:   daily aggregates by provider and model (usage, cost, latency).

These tables are queried by the VPS via 'clawctl databricks query'.
"""

import dlt
from pyspark.sql.functions import (
    avg,
    col,
    count,
    date_trunc,
    sum as spark_sum,
)


@dlt.table(
    name="silver_sessions",
    comment="Parsed and deduplicated session events with typed columns",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("provider_present", "provider IS NOT NULL")
@dlt.expect_or_drop("positive_tokens", "tokens > 0")
def silver_sessions():  # type: ignore[return]
    """Read bronze, cast types, and drop duplicates."""
    return (
        dlt.read_stream("bronze_sessions")
        .select(
            col("session_id"),
            col("ts").cast("timestamp").alias("event_time"),
            col("provider"),
            col("model"),
            col("tokens").cast("int"),
            col("cost_usd").cast("double"),
            col("latency_ms").cast("int"),
            col("tool_calls").cast("int"),
            col("_source_file"),
            col("_ingested_at"),
        )
        .dropDuplicates(["session_id", "event_time"])
    )


@dlt.table(
    name="gold_daily_usage",
    comment="Daily aggregated usage: sessions, tokens, cost, and latency by provider/model",
    table_properties={"quality": "gold"},
)
def gold_daily_usage():  # type: ignore[return]
    """Aggregate silver_sessions to daily granularity."""
    return (
        dlt.read("silver_sessions")
        .withColumn("day", date_trunc("day", col("event_time")))
        .groupBy("day", "provider", "model")
        .agg(
            count("*").alias("session_count"),
            spark_sum("tokens").alias("total_tokens"),
            spark_sum("cost_usd").alias("total_cost_usd"),
            avg("latency_ms").alias("avg_latency_ms"),
        )
        .orderBy("day", "provider", "model")
    )
