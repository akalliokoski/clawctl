"""Tailscale/SSH access helpers."""

import subprocess
import time
import webbrowser

import typer
from rich.console import Console

from clawctl.ssh_utils import _validate_host

app = typer.Typer(help="Access OpenClaw via Tailscale")
console = Console()

DEFAULT_HOST = "openclaw-vps"
WEB_UI_PORT = 18789


@app.command("open")
def open_ui(
    host: str = typer.Option(DEFAULT_HOST, help="Tailscale hostname or IP"),
    port: int = typer.Option(WEB_UI_PORT, help="Web UI port"),
) -> None:
    """Open the OpenClaw web UI via an SSH tunnel (ports are localhost-only on the VPS)."""
    _validate_host(host)
    local_url = f"http://localhost:{port}"
    console.print(f"Starting SSH tunnel to {host}:{port}...")
    proc = subprocess.Popen(
        ["ssh", "-N", "-L", f"{port}:localhost:{port}", host],
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)
    console.print(f"Opening [link={local_url}]{local_url}[/link]")
    webbrowser.open(local_url)
    console.print("Press [bold]Ctrl+C[/bold] to close the tunnel.")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        console.print("\nTunnel closed.")


@app.command("ssh")
def ssh_connect(
    host: str = typer.Option(DEFAULT_HOST, help="Tailscale hostname or IP"),
) -> None:
    """Open an interactive SSH session to the VPS."""
    _validate_host(host)
    subprocess.run(["ssh", host], check=False)


@app.command("port-forward")
def port_forward(
    host: str = typer.Option(DEFAULT_HOST),
    remote_port: int = typer.Option(WEB_UI_PORT, help="Remote port to forward"),
    local_port: int = typer.Option(WEB_UI_PORT, help="Local port to bind"),
) -> None:
    """Set up an SSH port-forward as an alternative to Tailscale (fallback only)."""
    _validate_host(host)
    console.print(
        f"Forwarding localhost:{local_port} -> {host}:{remote_port}\n"
        f"Then open: http://localhost:{local_port}"
    )
    subprocess.run(
        ["ssh", "-N", "-L", f"{local_port}:localhost:{remote_port}", host],
        check=False,
    )
