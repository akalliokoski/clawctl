"""Deploy and update OpenClaw on VPS."""

import os
import re
import shlex

import typer
from rich.console import Console

from clawctl.ssh_utils import run_cmd, upload_file

app = typer.Typer(help="Deploy and update OpenClaw")
console = Console()

REMOTE_DIR = "/opt/openclaw"

# Allowed channel names for pairing (prevents injection)
_VALID_CHANNEL_RE = re.compile(r"^[a-z][a-z0-9_-]{0,30}$")
# Pairing codes are typically hex or alphanumeric
_VALID_CODE_RE = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


@app.command("push")
def push(
    host: str = typer.Option("openclaw-vps", help="Tailscale hostname or IP"),
    compose_file: str = typer.Option(
        "docker/docker-compose.yml", help="Local path to docker-compose.yml"
    ),
    env_file: str = typer.Option(
        ".env.production", help="Local path to .env file (never commit this!)"
    ),
) -> None:
    """Upload configs and redeploy OpenClaw on the VPS."""
    for path in [compose_file, env_file]:
        if not os.path.exists(path):
            console.print(f"[red]File not found: {path}[/red]")
            raise typer.Exit(1)

    with console.status("Uploading configs..."):
        upload_file(host, compose_file, f"{REMOTE_DIR}/docker-compose.yml")
        upload_file(host, env_file, f"{REMOTE_DIR}/.env")

    with console.status("Pulling latest image and restarting..."):
        run_cmd(host, f"cd {REMOTE_DIR} && docker compose pull && docker compose up -d")

    output = run_cmd(host, "docker ps --format '{{.Names}}: {{.Status}}'")
    console.print(f"[green]Deployed.[/green]\n{output}")


@app.command("logs")
def logs(
    host: str = typer.Option("openclaw-vps"),
    lines: int = typer.Option(50, help="Number of log lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
) -> None:
    """Tail OpenClaw container logs."""
    if follow:
        console.print(
            "[bold]Follow mode requires an interactive SSH session.[/bold]\n"
            f"  Run: ssh {host} docker logs -f openclaw"
        )
        return
    # lines is typed as int by typer, safe to interpolate
    output = run_cmd(host, f"docker logs --tail {int(lines)} openclaw 2>&1")
    typer.echo(output)


@app.command("restart")
def restart(
    host: str = typer.Option("openclaw-vps"),
) -> None:
    """Restart the OpenClaw container."""
    with console.status("Restarting..."):
        run_cmd(host, f"cd {REMOTE_DIR} && docker compose restart")
    console.print("[green]Restarted.[/green]")


@app.command("onboard")
def onboard(
    host: str = typer.Option("openclaw-vps"),
) -> None:
    """Run the OpenClaw interactive onboarding wizard on the VPS."""
    console.print("[bold]Running onboarding wizard (interactive — you may need to SSH in manually)[/bold]")
    console.print(
        f"  ssh {host} \"docker compose -f {REMOTE_DIR}/docker-compose.yml exec openclaw"
        " node dist/index.js onboard\""
    )


@app.command("pairing")
def pairing(
    code: str = typer.Argument(..., help="Pairing code received from Telegram bot"),
    host: str = typer.Option("openclaw-vps"),
    channel: str = typer.Option("telegram", help="Channel type (telegram, discord, etc.)"),
) -> None:
    """Approve a Telegram (or other channel) pairing code."""
    # Validate inputs to prevent command injection
    if not _VALID_CHANNEL_RE.match(channel):
        console.print(f"[red]Invalid channel name: {channel!r}[/red]")
        raise typer.Exit(1)
    if not _VALID_CODE_RE.match(code):
        console.print(f"[red]Invalid pairing code format: {code!r}[/red]")
        raise typer.Exit(1)

    with console.status("Approving pairing code..."):
        output = run_cmd(
            host,
            f"docker exec openclaw openclaw pairing approve"
            f" {shlex.quote(channel)} {shlex.quote(code)}",
        )
    console.print(f"[green]Approved.[/green]\n{output}")
