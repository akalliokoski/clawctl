"""Hetzner VPS provisioning commands."""

import os

import typer
from hcloud import Client
from hcloud.images import Image
from hcloud.locations import Location
from hcloud.server_types import ServerType
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Hetzner server management")
console = Console()


def get_client() -> Client:
    token = os.environ.get("HCLOUD_TOKEN")
    if not token:
        typer.echo("Error: HCLOUD_TOKEN env var is not set.", err=True)
        raise typer.Exit(1)
    return Client(token=token)


@app.command("create")
def create(
    name: str = typer.Option("openclaw-vps", help="Server name"),
    server_type: str = typer.Option("cx33", help="Hetzner server type (cx33 recommended)"),
    image: str = typer.Option("ubuntu-24.04", help="OS image"),
    location: str = typer.Option("nbg1", help="Datacenter location (nbg1, fsn1, hel1)"),
    ssh_key: str = typer.Option("openclaw-key", help="Name of SSH key uploaded to Hetzner"),
    firewall: str = typer.Option("openclaw-fw", help="Firewall name to apply (optional)"),
) -> None:
    """Provision a new Hetzner VPS for OpenClaw."""
    client = get_client()
    with console.status(f"Provisioning [bold]{name}[/bold] ({server_type}) in {location}..."):
        key = client.ssh_keys.get_by_name(ssh_key)
        if not key:
            console.print(f"[yellow]Warning: SSH key '{ssh_key}' not found — continuing without it.[/yellow]")

        resp = client.servers.create(
            name=name,
            server_type=ServerType(name=server_type),
            image=Image(name=image),
            location=Location(name=location),
            ssh_keys=[key] if key else [],
        )
        resp.action.wait_until_finished()

    ip = resp.server.public_net.ipv4.ip
    console.print(f"[green]Server created:[/green] {name} @ {ip}")

    fw = client.firewalls.get_by_name(firewall)
    if fw:
        with console.status("Applying firewall..."):
            fw.apply_to_resources([{"type": "server", "server": {"id": resp.server.id}}])
        console.print(f"[green]Firewall '{firewall}' applied.[/green]")

    console.print("\nNext steps:")
    console.print(f"  1. scp scripts/bootstrap-vps.sh root@{ip}:/tmp/")
    console.print(f"  2. ssh root@{ip} 'bash /tmp/bootstrap-vps.sh'")
    console.print(f"  3. ssh root@{ip} 'tailscale up --ssh'")


@app.command("destroy")
def destroy(
    name: str = typer.Argument(..., help="Server name to destroy"),
) -> None:
    """Permanently destroy a Hetzner server."""
    typer.confirm(f"Permanently destroy server '{name}'? This cannot be undone.", abort=True)
    client = get_client()
    srv = client.servers.get_by_name(name)
    if not srv:
        console.print(f"[red]Server '{name}' not found.[/red]")
        raise typer.Exit(1)
    client.servers.delete(srv)
    console.print(f"[red]Destroyed:[/red] {name}")


@app.command("ip")
def get_ip(
    name: str = typer.Option("openclaw-vps", help="Server name"),
) -> None:
    """Print the public IPv4 address of a server."""
    client = get_client()
    srv = client.servers.get_by_name(name)
    if not srv:
        console.print(f"[red]Server '{name}' not found.[/red]")
        raise typer.Exit(1)
    typer.echo(srv.public_net.ipv4.ip)


@app.command("list")
def list_servers() -> None:
    """List all Hetzner servers in this project."""
    client = get_client()
    servers = client.servers.get_all()
    if not servers:
        console.print("No servers found.")
        return

    table = Table(title="Hetzner Servers")
    table.add_column("Name", style="cyan")
    table.add_column("IP", style="green")
    table.add_column("Type")
    table.add_column("Location")
    table.add_column("Status")

    for s in servers:
        table.add_row(
            s.name,
            s.public_net.ipv4.ip,
            s.server_type.name,
            s.datacenter.location.name,
            f"[green]{s.status}[/green]" if s.status == "running" else s.status,
        )

    console.print(table)


@app.command("ssh-key-upload")
def ssh_key_upload(
    key_name: str = typer.Option("openclaw-key", help="Name for the key in Hetzner"),
    pub_key_path: str = typer.Option(
        "~/.ssh/openclaw_ed25519.pub", help="Path to the public key file"
    ),
) -> None:
    """Upload a local SSH public key to Hetzner."""
    path = os.path.expanduser(pub_key_path)
    if not os.path.exists(path):
        console.print(f"[red]Key file not found: {path}[/red]")
        raise typer.Exit(1)

    client = get_client()
    with open(path) as f:
        pub_key = f.read().strip()

    existing = client.ssh_keys.get_by_name(key_name)
    if existing:
        console.print(f"[yellow]Key '{key_name}' already exists in Hetzner.[/yellow]")
        return

    client.ssh_keys.create(name=key_name, public_key=pub_key)
    console.print(f"[green]Uploaded SSH key:[/green] {key_name}")
