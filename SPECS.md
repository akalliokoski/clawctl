# OpenClaw on Hetzner — Specs & Self-Hosting Guide

A practical reference for provisioning a Hetzner VPS, deploying OpenClaw via
Docker, securing access with Tailscale, connecting Telegram and OpenRouter, and
managing everything with the `clawctl` Python CLI.

---

## Table of Contents

1. [Stack Overview](#1-stack-overview)
2. [Prerequisites](#2-prerequisites)
3. [Provision the Hetzner VPS](#3-provision-the-hetzner-vps)
4. [Secure Access with Tailscale](#4-secure-access-with-tailscale)
5. [Deploy OpenClaw with Docker](#5-deploy-openclaw-with-docker)
6. [Configure OpenRouter as the LLM Provider](#6-configure-openrouter-as-the-llm-provider)
7. [Connect Telegram Natively](#7-connect-telegram-natively)
8. [Enable Skills](#8-enable-skills)
9. [clawctl CLI Reference](#9-clawctl-cli-reference)
10. [Full Deploy Sequence (Zero to Running)](#10-full-deploy-sequence-zero-to-running)
11. [Security Considerations](#11-security-considerations)
12. [Costs](#12-costs)
13. [Project Structure](#13-project-structure)

---

## 1. Stack Overview

| Component          | Choice                                    | Why                                                  |
|--------------------|-------------------------------------------|------------------------------------------------------|
| VPS                | Hetzner CX33 (4 vCPU, 8 GB RAM, 80 GB)   | €5.49/mo, plenty for Docker + OpenClaw               |
| OS                 | Ubuntu 24.04 LTS                          | Newer kernel, longer support, full Docker compat     |
| Agent              | OpenClaw (latest)                         | Web UI, skills, native Telegram, OpenRouter          |
| LLM                | OpenRouter → Claude Sonnet 4.5            | One API key, access to 200+ models                   |
| Access             | Tailscale                                 | Zero public ports, MagicDNS, always-on VPN           |
| Secrets            | `.env` files                              | Simple, Git-ignored, uploaded via SCP                |
| CLI                | `clawctl` (Typer + hcloud SDK + Paramiko) | Provision, deploy, manage from macOS terminal        |
| Companion services | None                                      | OpenClaw uses file-based state (`~/.openclaw/`)      |

**About OpenClaw:** OpenClaw (160k+ GitHub stars, formerly Clawdbot → Moltbot →
OpenClaw, Jan 2026, created by Peter Steinberger) is a self-hosted agent runtime
and message router. It's a long-running Node.js service that connects messaging
channels (Telegram, WhatsApp, Discord, Slack, and 8+ others) to AI agents
capable of executing real-world tasks: shell commands, browser control, file
operations, web search, email, and more.

- GitHub: `github.com/openclaw/openclaw`
- Docs: `docs.openclaw.ai`
- Web UI: port `18789` by default

No Redis or Postgres required — all state is stored as flat files under
`~/.openclaw/`.

---

## 2. Prerequisites

### macOS tools

```bash
brew install hcloud          # Hetzner CLI
brew install --cask tailscale
brew install uv              # Python package manager
```

### SSH key for the VPS

```bash
ssh-keygen -t ed25519 -C "openclaw-vps" -f ~/.ssh/openclaw_ed25519
```

Add to `~/.ssh/config`:

```sshconfig
Host openclaw-vps
    HostName openclaw-vps        # Tailscale MagicDNS name
    User root
    IdentityFile ~/.ssh/openclaw_ed25519
    IdentitiesOnly yes
```

### Hetzner API token

1. Go to [console.hetzner.cloud](https://console.hetzner.cloud) → Security → API Tokens
2. Create a Read/Write token
3. Export: `export HCLOUD_TOKEN="your-token"`

---

## 3. Provision the Hetzner VPS

### Server sizes

| Type  | vCPU | RAM   | SSD    | Price   | Recommendation             |
|-------|------|-------|--------|---------|----------------------------|
| CX23  | 2    | 4 GB  | 40 GB  | €3.49/mo | Testing only — tight with browser skills |
| CX33  | 4    | 8 GB  | 80 GB  | €5.49/mo | **Recommended for production** |
| CX43  | 8    | 16 GB | 160 GB | €9.49/mo | Heavy browser automation   |

### Upload SSH key and create server

```bash
# Upload SSH key
hcloud ssh-key create --name openclaw-key \
    --public-key-from-file ~/.ssh/openclaw_ed25519.pub

# Create firewall (SSH + ICMP only — everything else via Tailscale)
hcloud firewall create --name openclaw-fw
hcloud firewall add-rule openclaw-fw \
    --direction in --source-ips 0.0.0.0/0 --source-ips ::/0 \
    --protocol tcp --port 22 --description "SSH"
hcloud firewall add-rule openclaw-fw \
    --direction in --source-ips 0.0.0.0/0 --source-ips ::/0 \
    --protocol icmp --description "Ping"

# Launch the server
hcloud server create \
    --name openclaw-vps \
    --type cx33 \
    --image ubuntu-24.04 \
    --location nbg1 \
    --ssh-key openclaw-key

# Apply firewall
hcloud firewall apply-to-resource openclaw-fw \
    --type server --server openclaw-vps
```

Or use `clawctl`:

```bash
clawctl server ssh-key-upload
clawctl server create --server-type cx33
```

### Using cloud-init for automated bootstrap

Pass `config/cloud-init.yaml` at creation time to skip the manual bootstrap:

```bash
hcloud server create \
    --name openclaw-vps \
    --type cx33 \
    --image ubuntu-24.04 \
    --location nbg1 \
    --ssh-key openclaw-key \
    --user-data-from-file config/cloud-init.yaml
```

---

## 4. Secure Access with Tailscale

Tailscale beats SSH tunnels: you get a persistent private network where every
port on the VPS is accessible via its Tailscale IP with zero public exposure.
Free for personal use (up to 100 devices).

### On the VPS (first time)

```bash
ssh -i ~/.ssh/openclaw_ed25519 root@$(hcloud server ip openclaw-vps)

curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --ssh
# Open the printed URL in your browser to authenticate
# Then in Tailscale admin: Machines → openclaw-vps → Disable key expiry
```

### On macOS

```bash
open -a Tailscale   # Log in with the same account used for the VPS
```

### Lock down UFW to Tailscale-only

```bash
# On the VPS:
ufw default deny incoming
ufw default allow outgoing
ufw allow in on tailscale0   # All Tailscale traffic
ufw allow 22/tcp              # SSH fallback on public IP
ufw enable
```

### Verify

```bash
tailscale status                   # Both devices should appear
ssh root@openclaw-vps              # MagicDNS name works
curl http://openclaw-vps:18789     # Web UI via Tailscale
```

---

## 5. Deploy OpenClaw with Docker

### Directory structure on the VPS

```
/opt/openclaw/
├── docker-compose.yml
├── .env
├── data/         # openclaw config/memory/skills (chown 1000:1000)
└── workspace/    # agent working files (chown 1000:1000)
```

### Environment variables (`.env`)

Generate the gateway token with `openssl rand -hex 32`.

```dotenv
OPENCLAW_GATEWAY_TOKEN=<openssl rand -hex 32>
OPENROUTER_API_KEY=sk-or-v1-...
TELEGRAM_BOT_TOKEN=123456789:ABC...
BRAVE_API_KEY=BSA...
OPENCLAW_CONFIG_DIR=/opt/openclaw/data
OPENCLAW_WORKSPACE_DIR=/opt/openclaw/workspace
```

### Key `docker-compose.yml` notes

- Ports are bound to `127.0.0.1` — not exposed on the public IP.
- Tailscale traffic still reaches them because Tailscale operates at OS level.
- `restart: unless-stopped` keeps OpenClaw running across reboots.
- `init: true` ensures clean signal handling inside the container.

### Deploy

```bash
# First time — manual bootstrap
scp scripts/bootstrap-vps.sh root@$(hcloud server ip openclaw-vps):/tmp/
ssh root@$(hcloud server ip openclaw-vps) bash /tmp/bootstrap-vps.sh

# Upload compose + env
clawctl deploy push --compose-file docker/docker-compose.yml \
                    --env-file .env.production

# Run onboarding wizard
ssh openclaw-vps "docker compose -f /opt/openclaw/docker-compose.yml \
    exec openclaw node dist/index.js onboard"
```

### Access the web UI

```bash
clawctl tunnel open   # Opens http://openclaw-vps:18789 in your browser
```

---

## 6. Configure OpenRouter as the LLM Provider

OpenRouter provides a single API key routing to 200+ models. Set
`OPENROUTER_API_KEY` in your `.env`. Model names follow the format
`openrouter/<author>/<slug>`.

### Recommended models

| Use case               | Model                                        | Notes                         |
|------------------------|----------------------------------------------|-------------------------------|
| Daily driver / code    | `openrouter/anthropic/claude-sonnet-4-5`     | Best balance of cost/quality  |
| Quick responses        | `openrouter/anthropic/claude-haiku-3-5`      | Fast, cheap                   |
| Complex reasoning      | `openrouter/anthropic/claude-opus-4`         | Highest quality               |
| Cost auto-optimization | `openrouter/openrouter/auto`                 | Routes by task complexity     |
| Free tier testing      | `openrouter/openai/gpt-oss-120b:free`        | No cost                       |

### `config/openclaw.json` (agent defaults)

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "openrouter/anthropic/claude-sonnet-4-5",
        "fallbacks": [
          "openrouter/anthropic/claude-haiku-3-5",
          "openrouter/google/gemini-pro-1-5"
        ]
      }
    }
  }
}
```

---

## 7. Connect Telegram Natively

OpenClaw has first-class Telegram support (grammY internally). Supports DMs,
groups, forum topics, inline keyboards, media, stickers, and reactions.

### Setup

1. Create a bot via `@BotFather` on Telegram → `/newbot` → copy the token.
2. Set `TELEGRAM_BOT_TOKEN` in `.env`.
3. Restart and approve the first pairing:

```bash
docker compose restart openclaw
# Send any message to your bot on Telegram — it returns a pairing code
clawctl deploy pairing <CODE>
```

### DM policies

| Policy    | Behaviour                                                        |
|-----------|------------------------------------------------------------------|
| `pairing` | (default) New users get a code you approve via CLI              |
| `allowlist` | Only specific Telegram user IDs in `allowFrom` array          |
| `open`    | Anyone can message — **dangerous with capable agents**           |

---

## 8. Enable Skills

### Built-in core tools (always available)

`Read`, `Write`, `Edit`, `Bash/Exec`, `web_search`, `web_fetch`, `Glob`, `Grep`

### Web search

Auto-detects providers in priority order: Brave → Gemini → Perplexity → Grok.
Set at least one API key and configure:

```json
{ "tools": { "web": { "search": { "provider": "brave" } } } }
```

### Browser automation

```json
{ "browser": { "enabled": true, "headless": true, "defaultProfile": "openclaw" } }
```

For Docker, build the browser sandbox image:

```bash
docker compose exec openclaw bash scripts/sandbox-browser-setup.sh
```

### ClawHub community skills

```bash
docker compose exec openclaw clawhub install perplexity-sonar
docker compose exec openclaw clawhub install triple-memory
docker compose exec openclaw clawhub install nano-banana-pro   # Gemini image gen
```

Skills live in `~/.openclaw/skills/` as folders with `SKILL.md` files
(YAML frontmatter). They are auto-loaded and auto-gated based on required
env vars and binaries.

### Custom skills

See `skills/my-custom-skill/SKILL.md` for a template. Sync to the VPS:

```bash
rsync -avz skills/ root@openclaw-vps:/opt/openclaw/data/skills/
```

---

## 9. clawctl CLI Reference

Install locally with `uv`:

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install clawctl
uv sync
uv run clawctl --help

# Or install globally (editable)
uv pip install -e .
```

### `server` — Hetzner provisioning

```bash
clawctl server list
clawctl server create [--name openclaw-vps] [--server-type cx33] [--location nbg1]
clawctl server destroy openclaw-vps
clawctl server ip [--name openclaw-vps]
clawctl server ssh-key-upload [--key-name openclaw-key] [--pub-key-path ~/.ssh/openclaw_ed25519.pub]
```

### `deploy` — Deploy and update OpenClaw

```bash
clawctl deploy push [--host openclaw-vps] [--compose-file docker/docker-compose.yml] \
                    [--env-file .env.production]
clawctl deploy logs [--host openclaw-vps] [--lines 100] [--follow]
clawctl deploy restart [--host openclaw-vps]
clawctl deploy onboard [--host openclaw-vps]          # prints the manual command
clawctl deploy pairing <CODE> [--host openclaw-vps] [--channel telegram]
```

### `status` — Health checks

```bash
clawctl status check [--host openclaw-vps]
clawctl status doctor [--host openclaw-vps]
clawctl status disk [--host openclaw-vps]
clawctl status tailscale [--host openclaw-vps]
```

### `tunnel` — Access helpers

```bash
clawctl tunnel open [--host openclaw-vps] [--port 18789]   # Opens browser (macOS)
clawctl tunnel ssh [--host openclaw-vps]                    # Interactive SSH session
clawctl tunnel port-forward [--remote-port 18789] [--local-port 18789]
```

---

## 10. Full Deploy Sequence (Zero to Running)

From your Mac, zero to running agent in ~10 minutes:

```bash
# 1. Provision
export HCLOUD_TOKEN="your-token"
clawctl server ssh-key-upload
clawctl server create

# 2. Bootstrap (first time only)
scp scripts/bootstrap-vps.sh root@$(clawctl server ip):/tmp/
ssh root@$(clawctl server ip) bash /tmp/bootstrap-vps.sh
ssh root@$(clawctl server ip) tailscale up --ssh
# → Approve in Tailscale admin console, disable key expiry

# 3. Deploy
cp .env.example .env.production   # Fill in real values
clawctl deploy push --env-file .env.production

# 4. Onboard
clawctl deploy onboard
# Copy/paste the printed command into your terminal

# 5. Open the web UI
clawctl tunnel open   # Opens http://openclaw-vps:18789

# 6. Approve Telegram pairing
# Send a message to your bot → get pairing code
clawctl deploy pairing <CODE>
```

### Ongoing operations

```bash
# Check health
clawctl status check

# Update to latest OpenClaw image
clawctl deploy push

# View recent logs
clawctl deploy logs --lines 100

# Backup data to ./backups/
./scripts/backup.sh
```

---

## 11. Security Considerations

> CrowdStrike and Cisco's AI security team have both analyzed OpenClaw. The
> framework requires broad permissions (shell access, file system, browser
> control) to function effectively, which creates real risk if misconfigured.

| Risk                        | Mitigation                                                         |
|-----------------------------|---------------------------------------------------------------------|
| Overspending on LLM APIs    | Set hard spending limits on your OpenRouter account                |
| Telegram bot abuse          | Use `pairing` or `allowlist` DM policy — **never `open`**          |
| Web UI exposure             | Keep port 18789 behind Tailscale — **never expose publicly**       |
| Weak gateway auth           | Use `openssl rand -hex 32` for `OPENCLAW_GATEWAY_TOKEN`            |
| Malicious skills            | Enable sandbox mode; review `SKILL.md` before installing from Hub  |
| Browser automation escapes  | Run browser container sandboxed, not on the host                   |
| Secrets in Git              | `.env` is in `.gitignore`; only `.env.example` is committed        |

### Firewall rules summary

The UFW config locks down the server to:
- Tailscale interface (`tailscale0`) — all ports accessible internally
- Port 22/tcp on the public IP — SSH fallback only
- Everything else blocked on the public IP

---

## 12. Costs

| Item              | Cost                                        |
|-------------------|---------------------------------------------|
| Hetzner CX33 VPS  | ~€5.49/mo                                   |
| OpenRouter (casual) | < $10/mo at Claude Sonnet 4.5 rates       |
| Tailscale         | Free for personal use (up to 100 devices)   |
| **Total**         | **~€10–15/mo all-in**                       |

Claude Sonnet 4.5 pricing: ~$3/M input tokens, $15/M output tokens.

---

## 13. Project Structure

```
clawctl/
├── README.md
├── SPECS.md                      ← This file
├── .gitignore
├── .env.example                  ← Template — never commit real .env
├── pyproject.toml                ← uv/hatch project config
│
├── clawctl/                      ← Python CLI package
│   ├── __init__.py
│   ├── main.py                   ← Typer app entry point
│   ├── server.py                 ← Hetzner provisioning commands
│   ├── deploy.py                 ← Deploy/update commands
│   ├── status.py                 ← Health check commands
│   ├── tunnel.py                 ← Tailscale/SSH access helpers
│   └── ssh_utils.py              ← Paramiko SSH/SFTP wrapper
│
├── docker/
│   ├── docker-compose.yml        ← Production compose file
│   └── docker-compose.dev.yml    ← Local dev overrides
│
├── config/
│   ├── openclaw.json             ← OpenClaw config template
│   └── cloud-init.yaml           ← Auto-setup on server create
│
├── scripts/
│   ├── bootstrap-vps.sh          ← First-time VPS setup
│   └── backup.sh                 ← Backup ~/.openclaw from VPS
│
└── skills/
    └── my-custom-skill/
        └── SKILL.md              ← Custom skill template
```
