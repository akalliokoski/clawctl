"""Entry point for the clawctl CLI."""

import typer
from dotenv import load_dotenv

from clawctl import databricks, deploy, server, status, tunnel

# Load .env / .env.production so HCLOUD_TOKEN etc. are available without
# the user having to export them manually in every shell session.
load_dotenv()  # .env
load_dotenv(".env.production")  # project-specific overrides

app = typer.Typer(
    name="clawctl",
    help="OpenClaw VPS management CLI — provision, deploy, and manage from your terminal.",
    no_args_is_help=True,
)

app.add_typer(server.app, name="server")
app.add_typer(deploy.app, name="deploy")
app.add_typer(status.app, name="status")
app.add_typer(tunnel.app, name="tunnel")
app.add_typer(databricks.app, name="databricks")


if __name__ == "__main__":
    app()
