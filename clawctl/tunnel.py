"""Tailscale/SSH access helpers."""

import subprocess

import typer
from rich.console import Console

app = typer.Typer(help="Access OpenClaw via Tailscale")
console = Console()

DEFAULT_HOST = "openclaw-vps"
WEB_UI_PORT = 18789


@app.command("open")
def open_ui(
    host: str = typer.Option(DEFAULT_HOST, help="Tailscale hostname or IP"),
    port: int = typer.Option(WEB_UI_PORT, help="Web UI port"),
) -> None:
    """Open the OpenClaw web UI in the default browser (macOS)."""
    url = f"http://{host}:{port}"
    console.print(f"Opening [link={url}]{url}[/link]")
    subprocess.run(["open", url], check=False)  # macOS; use xdg-open on Linux


@app.command("ssh")
def ssh_connect(
    host: str = typer.Option(DEFAULT_HOST, help="Tailscale hostname or IP"),
) -> None:
    """Open an interactive SSH session to the VPS."""
    subprocess.run(["ssh", host], check=False)


@app.command("port-forward")
def port_forward(
    host: str = typer.Option(DEFAULT_HOST),
    remote_port: int = typer.Option(WEB_UI_PORT, help="Remote port to forward"),
    local_port: int = typer.Option(WEB_UI_PORT, help="Local port to bind"),
) -> None:
    """Set up an SSH port-forward as an alternative to Tailscale (fallback only)."""
    console.print(
        f"Forwarding localhost:{local_port} → {host}:{remote_port}\n"
        f"Then open: http://localhost:{local_port}"
    )
    subprocess.run(
        ["ssh", "-N", "-L", f"{local_port}:localhost:{remote_port}", host],
        check=False,
    )
