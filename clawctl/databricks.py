"""Databricks Free Edition integration — upload data and query via REST APIs.

Uses only the Python standard library (urllib) so no extra dependencies are needed.
Authentication: set DATABRICKS_HOST and DATABRICKS_TOKEN in your .env file.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Databricks Free Edition — upload data and run SQL queries")
console = Console()

# Default Unity Catalog paths matching the Terraform config
_DEFAULT_CATALOG = "dev_catalog"
_DEFAULT_SCHEMA = "openclaw_data"
_DEFAULT_VOLUME_PATH = f"/Volumes/{_DEFAULT_CATALOG}/{_DEFAULT_SCHEMA}/landing"

# Validates catalog.schema.table — three dot-separated identifiers only
_TABLE_RE = re.compile(r"^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_credentials() -> tuple[str, dict[str, str]]:
    """Return (host, auth_headers) from env, or print an error and exit."""
    host = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
    token = os.environ.get("DATABRICKS_TOKEN", "")
    if not host or not token:
        console.print(
            "[red]DATABRICKS_HOST and DATABRICKS_TOKEN must be set.[/red]\n"
            "Get a PAT from: Databricks workspace → User Settings → Developer → Access tokens",
            highlight=False,
        )
        raise typer.Exit(1)
    headers = {"Authorization": f"Bearer {token}"}
    return host, headers


def _api_get(host: str, headers: dict[str, str], path: str) -> Any:
    """GET a Databricks REST endpoint and return the parsed JSON body."""
    req = urllib.request.Request(
        f"{host}{path}",
        headers=headers,
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def _sql_exec(
    host: str,
    headers: dict[str, str],
    statement: str,
    warehouse_id: str,
    parameters: list[dict[str, str]] | None = None,
    poll_timeout: int = 60,
) -> dict[str, Any]:
    """Submit SQL via the Statement Execution API and poll until complete."""
    body: dict[str, Any] = {
        "warehouse_id": warehouse_id,
        "statement": statement,
        "wait_timeout": "30s",
    }
    if parameters:
        body["parameters"] = parameters

    post_req = urllib.request.Request(
        f"{host}/api/2.0/sql/statements/",
        data=json.dumps(body).encode(),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(post_req, timeout=35) as resp:
            result: dict[str, Any] = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body_txt = exc.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body_txt}") from exc

    stmt_id = result.get("statement_id", "")
    deadline = time.monotonic() + poll_timeout

    while result.get("status", {}).get("state") in ("PENDING", "RUNNING"):
        if time.monotonic() > deadline:
            raise RuntimeError(f"SQL statement {stmt_id} timed out after {poll_timeout}s")
        time.sleep(2)
        poll_req = urllib.request.Request(
            f"{host}/api/2.0/sql/statements/{stmt_id}",
            headers=headers,
            method="GET",
        )
        try:
            with urllib.request.urlopen(poll_req, timeout=15) as resp:
                result = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body_txt = exc.read().decode(errors="replace")
            raise RuntimeError(f"Poll failed HTTP {exc.code}: {body_txt}") from exc

    return result


def _is_valid_json(s: str) -> bool:
    """Return True if *s* is parseable JSON."""
    try:
        json.loads(s)
        return True
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command("ping")
def ping() -> None:
    """Test Databricks connection and list available SQL warehouses."""
    host, headers = _get_credentials()
    try:
        data = _api_get(host, headers, "/api/2.0/sql/warehouses")
    except RuntimeError as exc:
        console.print(f"[red]Connection failed: {exc}[/red]")
        raise typer.Exit(1) from None

    warehouses = data.get("warehouses", [])
    if not warehouses:
        console.print(f"[yellow]Connected to {host} — no SQL warehouses found yet.[/yellow]")
        return

    table = Table(title=f"SQL Warehouses — {host}")
    table.add_column("Name", style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("State")
    table.add_column("Size")

    for wh in warehouses:
        state = wh.get("state", "UNKNOWN")
        color = "green" if state == "RUNNING" else "yellow"
        table.add_row(
            wh.get("name", ""),
            wh.get("id", ""),
            f"[{color}]{state}[/{color}]",
            wh.get("cluster_size", ""),
        )

    console.print(table)
    console.print(f"[green]Connected:[/green] {host}")


@app.command("upload")
def upload(
    file: str = typer.Argument(..., help="Local JSONL file to upload"),
    volume_path: str = typer.Option(
        _DEFAULT_VOLUME_PATH,
        help="Databricks Unity Catalog Volume path prefix",
    ),
    subdir: str = typer.Option(
        "sessions",
        help="Sub-directory within the volume (sessions, metrics, memory)",
    ),
) -> None:
    """Upload a JSONL file to a Unity Catalog Volume via the Files API.

    Equivalent to:
      curl -X PUT -H 'Authorization: Bearer $TOKEN' \\
        --data-binary @file.jsonl \\
        https://$HOST/api/2.0/fs/files/Volumes/.../landing/sessions/file.jsonl
    """
    host, headers = _get_credentials()
    src = Path(file)
    if not src.exists():
        console.print(f"[red]File not found: {src}[/red]")
        raise typer.Exit(1)

    dest_path = f"{volume_path.rstrip('/')}/{subdir}/{src.name}"
    url = f"{host}/api/2.0/fs/files{dest_path}"
    data = src.read_bytes()

    req = urllib.request.Request(
        url,
        data=data,
        headers={**headers, "Content-Type": "application/octet-stream"},
        method="PUT",
    )
    with console.status(f"Uploading {src.name} ({len(data):,} bytes)..."):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                resp.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            console.print(f"[red]Upload failed (HTTP {exc.code}): {body}[/red]")
            raise typer.Exit(1) from None

    console.print(f"[green]Uploaded:[/green] {dest_path}")


@app.command("query")
def query(
    sql: str = typer.Argument(..., help="SQL statement to execute"),
    warehouse_id: str = typer.Option(
        ...,
        envvar="DATABRICKS_WAREHOUSE_ID",
        help="SQL warehouse ID (or set DATABRICKS_WAREHOUSE_ID env var)",
    ),
    limit: int = typer.Option(100, help="Maximum rows to display"),
) -> None:
    """Execute a SQL query against a Databricks SQL warehouse and show results."""
    host, headers = _get_credentials()

    with console.status("Running query..."):
        try:
            result = _sql_exec(host, headers, sql, warehouse_id)
        except RuntimeError as exc:
            console.print(f"[red]Query error: {exc}[/red]")
            raise typer.Exit(1) from None

    state = result.get("status", {}).get("state", "UNKNOWN")
    if state != "SUCCEEDED":
        err = result.get("status", {}).get("error", {})
        console.print(f"[red]Query failed ({state}): {err.get('message', err)}[/red]")
        raise typer.Exit(1)

    schema = result.get("manifest", {}).get("schema", {})
    columns = [c["name"] for c in schema.get("columns", [])]
    rows: list[list[Any]] = result.get("result", {}).get("data_array", []) or []

    if not columns:
        console.print("[yellow]No results returned.[/yellow]")
        return

    tbl = Table(title=f"Results ({len(rows)} rows)")
    for col in columns:
        tbl.add_column(col, style="cyan")
    for row in rows[:limit]:
        tbl.add_row(*[str(v) if v is not None else "NULL" for v in row])

    console.print(tbl)
    if len(rows) > limit:
        console.print(f"[dim](showing {limit} of {len(rows)} rows)[/dim]")


@app.command("ingest")
def ingest(
    file: str = typer.Argument(..., help="Local JSONL file to ingest row-by-row"),
    table: str = typer.Option(
        f"{_DEFAULT_CATALOG}.{_DEFAULT_SCHEMA}.sessions_raw",
        help="Target Delta table as catalog.schema.table",
    ),
    warehouse_id: str = typer.Option(
        ...,
        envvar="DATABRICKS_WAREHOUSE_ID",
        help="SQL warehouse ID (or set DATABRICKS_WAREHOUSE_ID env var)",
    ),
    batch_size: int = typer.Option(50, help="JSON rows per INSERT statement"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without inserting"),
) -> None:
    """Insert JSONL rows into a Delta table via the SQL Statement Execution API.

    Each line in the file must be a valid JSON object. Lines that are not valid
    JSON are skipped with a warning. The target table is created automatically
    on first run with a raw_json STRING column.

    Use this command for low-volume ingestion (hundreds of rows per day).
    For higher volumes, use 'databricks upload' + a DLT pipeline instead.
    """
    if not _TABLE_RE.match(table):
        console.print(
            f"[red]Invalid table name {table!r} — must be catalog.schema.table "
            "(alphanumeric and underscores only).[/red]"
        )
        raise typer.Exit(1)

    src = Path(file)
    if not src.exists():
        console.print(f"[red]File not found: {src}[/red]")
        raise typer.Exit(1)

    lines = [ln.strip() for ln in src.read_text().splitlines() if ln.strip()]
    if not lines:
        console.print("[yellow]File is empty — nothing to ingest.[/yellow]")
        return

    valid_lines = [ln for ln in lines if _is_valid_json(ln)]
    skipped = len(lines) - len(valid_lines)
    if skipped:
        console.print(f"[yellow]Skipping {skipped} non-JSON lines.[/yellow]")

    console.print(f"Ingesting {len(valid_lines)} records into [cyan]{table}[/cyan]...")
    if dry_run:
        console.print(
            f"[yellow]Dry-run: would insert {len(valid_lines)} rows (no changes made).[/yellow]"
        )
        return

    host, headers = _get_credentials()
    inserted = 0
    errors = 0

    # Ensure the target table exists (idempotent)
    create_sql = (
        f"CREATE TABLE IF NOT EXISTS {table} "
        "(raw_json STRING, ingested_at TIMESTAMP DEFAULT current_timestamp())"
    )
    try:
        result = _sql_exec(host, headers, create_sql, warehouse_id)
        if result.get("status", {}).get("state") != "SUCCEEDED":
            console.print(f"[red]Could not create table {table}[/red]")
            raise typer.Exit(1)
    except RuntimeError as exc:
        console.print(f"[red]Table creation failed: {exc}[/red]")
        raise typer.Exit(1) from None

    for i in range(0, len(valid_lines), batch_size):
        batch = valid_lines[i : i + batch_size]
        # Escape single quotes in JSON strings for safe SQL literal embedding
        values = ", ".join(
            "('" + json.dumps(json.loads(row)).replace("'", "''") + "')"
            for row in batch
        )
        insert_sql = f"INSERT INTO {table} (raw_json) VALUES {values}"
        try:
            result = _sql_exec(host, headers, insert_sql, warehouse_id)
            if result.get("status", {}).get("state") == "SUCCEEDED":
                inserted += len(batch)
            else:
                err = result.get("status", {}).get("error", {})
                console.print(
                    f"[red]Batch {i // batch_size + 1} failed: {err.get('message', err)}[/red]"
                )
                errors += 1
        except RuntimeError as exc:
            console.print(f"[red]Batch {i // batch_size + 1} error: {exc}[/red]")
            errors += 1

    color = "green" if errors == 0 else "yellow"
    console.print(f"[{color}]Done: {inserted} rows inserted, {errors} batch errors.[/{color}]")
