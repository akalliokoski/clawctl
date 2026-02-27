# clawctl

CLI tool for provisioning, deploying, and managing [OpenClaw](https://github.com/openclaw/openclaw)
on a Hetzner VPS, secured with Tailscale.

> Full setup guide and specs: **[SPECS.md](SPECS.md)**

## Quick start

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Configure secrets
cp .env.example .env.production
# edit .env.production — fill in HCLOUD_TOKEN, OPENROUTER_API_KEY, etc.

# Provision a new VPS
export HCLOUD_TOKEN="your-token"
uv run clawctl server create

# Deploy OpenClaw
uv run clawctl deploy push --env-file .env.production

# Open the web UI (via Tailscale)
uv run clawctl tunnel open
```

## Commands

```
clawctl server   create / destroy / list / ip / ssh-key-upload
clawctl deploy   push / logs / restart / onboard / pairing
clawctl status   check / doctor / disk / tailscale
clawctl tunnel   open / ssh / port-forward
```

## Stack

- **VPS:** Hetzner CX33 (€5.49/mo)
- **Agent:** OpenClaw (Docker, file-based state)
- **LLM:** OpenRouter → Claude Sonnet 4.5
- **Access:** Tailscale (zero public ports)
- **CLI:** Typer + hcloud SDK + Paramiko

See [SPECS.md](SPECS.md) for the full self-hosting guide.
