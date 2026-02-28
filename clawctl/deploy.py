"""Deploy and update OpenClaw on VPS."""

import os
import re
import shlex
import subprocess
import tempfile

import typer
from rich.console import Console

from clawctl.ssh_utils import run_cmd, upload_file

app = typer.Typer(help="Deploy and update OpenClaw")
console = Console()

REMOTE_DIR = "/opt/openclaw"
CONFIG_FILE = f"{REMOTE_DIR}/data/openclaw.json"
MODELS_FILE = f"{REMOTE_DIR}/data/agents/main/agent/models.json"

# Allowed channel names for pairing (prevents injection)
_VALID_CHANNEL_RE = re.compile(r"^[a-z][a-z0-9_-]{0,30}$")
# Pairing codes are typically hex or alphanumeric
_VALID_CODE_RE = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")

_PATCH_SCRIPT = f"""\
import json
p = '{CONFIG_FILE}'
c = json.load(open(p))
c.setdefault('gateway', {{}})['mode'] = 'local'
ui = c['gateway'].setdefault('controlUi', {{}})
ui['allowedOrigins'] = ['http://localhost:18789']
ui.pop('dangerouslyAllowHostHeaderOriginFallback', None)
tg = c.setdefault('channels', {{}}).setdefault('telegram', {{}})
tg['dmPolicy'] = 'allowlist'
tg.setdefault('allowFrom', [])
open(p, 'w').write(json.dumps(c, indent=2))
print('Config patched OK')
"""


def _patch_config(host: str) -> None:
    """Upload a patch script and run it on the VPS — avoids shell quoting issues."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(_PATCH_SCRIPT)
        tmp = f.name
    try:
        upload_file(host, tmp, "/tmp/_clawctl_patch.py")
        out = run_cmd(host, "python3 /tmp/_clawctl_patch.py; rm /tmp/_clawctl_patch.py")
        console.print(f"  {out.strip()}")
    finally:
        os.unlink(tmp)


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
        subprocess.run(["ssh", host, "docker", "logs", "-f", "openclaw"], check=False)
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


@app.command("config-fix")
def config_fix(
    host: str = typer.Option("openclaw-vps"),
) -> None:
    """Patch gateway config and restart — run this if OpenClaw won't start after setup."""
    console.print("[bold]Patching gateway config...[/bold]")
    _patch_config(host)
    with console.status("Restarting..."):
        run_cmd(host, f"cd {REMOTE_DIR} && docker compose restart")
    console.print("[green]Done. Run 'clawctl tunnel open' to open the web UI.[/green]")


@app.command("onboard")
def onboard(
    host: str = typer.Option("openclaw-vps"),
) -> None:
    """Run the OpenClaw setup wizard, patch gateway config, and restart."""
    console.print("[bold]Step 1/3  Running setup wizard...[/bold]")
    result = subprocess.run([
        "ssh", "-t", host,
        f"docker compose -f {REMOTE_DIR}/docker-compose.yml run --rm openclaw node dist/index.js setup",
    ])
    if result.returncode not in (0, 130):  # 130 = Ctrl-C
        console.print(f"[red]Setup wizard exited {result.returncode}.[/red]")
        raise typer.Exit(result.returncode)

    console.print("[bold]Step 2/3  Patching gateway config...[/bold]")
    _patch_config(host)

    console.print("[bold]Step 3/3  Restarting OpenClaw...[/bold]")
    run_cmd(host, f"cd {REMOTE_DIR} && docker compose restart")
    console.print("[green]Done. Run 'clawctl tunnel open' to open the web UI.[/green]")


@app.command("telegram-allow")
def telegram_allow(
    user_id: int = typer.Argument(..., help="Telegram user ID to allow (get from @userinfobot)"),
    host: str = typer.Option("openclaw-vps"),
) -> None:
    """Add a Telegram user ID to the allowlist and set dmPolicy to allowlist."""
    script = f"""\
import json
p = '{CONFIG_FILE}'
c = json.load(open(p))
tg = c.setdefault('channels', {{}}).setdefault('telegram', {{}})
tg['dmPolicy'] = 'allowlist'
allowed = tg.setdefault('allowFrom', [])
if {user_id} not in allowed:
    allowed.append({user_id})
open(p, 'w').write(json.dumps(c, indent=2))
print('allowFrom:', allowed)
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        tmp = f.name
    try:
        upload_file(host, tmp, "/tmp/_clawctl_tg.py")
        out = run_cmd(host, "python3 /tmp/_clawctl_tg.py; rm /tmp/_clawctl_tg.py")
        console.print(f"  {out.strip()}")
    finally:
        os.unlink(tmp)

    with console.status("Restarting..."):
        run_cmd(host, f"cd {REMOTE_DIR} && docker compose restart")
    console.print(f"[green]User {user_id} added to Telegram allowlist.[/green]")


@app.command("configure-llm")
def configure_llm(
    model: str = typer.Option("moonshotai/kimi-k2", help="OpenRouter model ID (e.g. moonshotai/kimi-k2)"),
    host: str = typer.Option("openclaw-vps"),
) -> None:
    """Set the default LLM model via OpenRouter and restart."""
    script = f"""\
import json, os

models_path = '{MODELS_FILE}'
config_path = '{CONFIG_FILE}'
model_id = '{model}'

# Add model to models.json under openrouter provider
m = json.load(open(models_path))
provider = m.setdefault('providers', {{}}).setdefault('openrouter', {{}})
existing_ids = [x['id'] for x in provider.get('models', [])]
if model_id not in existing_ids:
    provider.setdefault('models', []).append({{
        'id': model_id,
        'name': model_id,
        'reasoning': False,
        'input': ['text', 'image'],
        'contextWindow': 131072,
        'maxTokens': 16384,
    }})
    print(f'Added {{model_id}} to models.json')
else:
    print(f'{{model_id}} already in models.json')
open(models_path, 'w').write(json.dumps(m, indent=2))

# Set default model in openclaw.json
c = json.load(open(config_path))
c.setdefault('agents', {{}}).setdefault('defaults', {{}})['model'] = {{
    'primary': f'openrouter/{{model_id}}',
}}
open(config_path, 'w').write(json.dumps(c, indent=2))
print(f'Default model set to openrouter/{{model_id}}')
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        tmp = f.name
    try:
        upload_file(host, tmp, "/tmp/_clawctl_llm.py")
        out = run_cmd(host, "python3 /tmp/_clawctl_llm.py; rm /tmp/_clawctl_llm.py")
        console.print(f"  {out.strip()}")
    finally:
        os.unlink(tmp)

    with console.status("Restarting..."):
        run_cmd(host, f"cd {REMOTE_DIR} && docker compose restart")
    console.print(f"[green]LLM configured: openrouter/{model}[/green]")


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
            f"docker compose -f {REMOTE_DIR}/docker-compose.yml exec openclaw"
            f" node dist/index.js pairing approve {shlex.quote(channel)} {shlex.quote(code)}",
        )
    console.print(f"[green]Approved.[/green]\n{output}")
