"""Entry point for the clawctl CLI."""

import typer

from clawctl import deploy, server, status, tunnel

app = typer.Typer(
    name="clawctl",
    help="OpenClaw VPS management CLI — provision, deploy, and manage from your terminal.",
    no_args_is_help=True,
)

app.add_typer(server.app, name="server")
app.add_typer(deploy.app, name="deploy")
app.add_typer(status.app, name="status")
app.add_typer(tunnel.app, name="tunnel")


if __name__ == "__main__":
    app()
