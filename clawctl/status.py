"""Health check and diagnostics commands."""

import typer
from rich.console import Console

from clawctl.ssh_utils import run_cmd

app = typer.Typer(help="Check OpenClaw health and status")
console = Console()


@app.command("check")
def check(
    host: str = typer.Option("openclaw-vps"),
) -> None:
    """Check whether OpenClaw containers are running."""
    output = run_cmd(
        host,
        "docker ps --format '{{.Names}}: {{.Status}}' --filter name=openclaw",
    )
    if output.strip():
        console.print(output)
    else:
        console.print("[red]No OpenClaw containers are running.[/red]")


@app.command("doctor")
def doctor(
    host: str = typer.Option("openclaw-vps"),
) -> None:
    """Run built-in OpenClaw diagnostics."""
    output = run_cmd(host, "docker exec openclaw openclaw doctor")
    console.print(output)


@app.command("disk")
def disk(
    host: str = typer.Option("openclaw-vps"),
) -> None:
    """Show disk usage on the VPS."""
    output = run_cmd(host, "df -h / && du -sh /opt/openclaw/data /opt/openclaw/workspace 2>/dev/null")
    console.print(output)


@app.command("tailscale")
def tailscale_status(
    host: str = typer.Option("openclaw-vps"),
) -> None:
    """Show Tailscale connectivity status on the VPS."""
    output = run_cmd(host, "tailscale status")
    console.print(output)
