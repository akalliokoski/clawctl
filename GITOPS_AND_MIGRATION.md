# OpenClaw GitOps & Migration Guide

A comprehensive reference for keeping your OpenClaw VPS setup in version control,
managing deployments as code, enabling skills self-modification with automatic PR
sync, and migrating the entire stack to a new VPS.

---

## Table of Contents

1. [GitOps Philosophy](#1-gitops-philosophy)
2. [What Lives in Git vs. What Stays on the VPS](#2-what-lives-in-git-vs-what-stays-on-the-vps)
3. [Recommended Repository Structure](#3-recommended-repository-structure)
4. [GitHub Actions: CI and Auto-Deploy](#4-github-actions-ci-and-auto-deploy)
5. [Watchtower: Auto-Update Docker Images](#5-watchtower-auto-update-docker-images)
6. [Skills as Code: Version Control & Deployment](#6-skills-as-code-version-control--deployment)
7. [OpenClaw Self-Modification: Auto-PR Workflow](#7-openclaw-self-modification-auto-pr-workflow)
8. [Migration Guide: Moving to a New VPS](#8-migration-guide-moving-to-a-new-vps)
9. [Backup Strategy](#9-backup-strategy)
10. [Disaster Recovery Checklist](#10-disaster-recovery-checklist)
11. [Tricks & Tips](#11-tricks--tips)

---

## 1. GitOps Philosophy

**Core principle**: The Git repository is the single source of truth for all OpenClaw
configuration and code. The VPS state is always derivable from the repository — no
manual config drift, no "I remember I changed that once" surprises.

What this means in practice:

- Every config change is a PR, reviewed before it hits the VPS
- Every VPS state is reproducible from `git clone` + a secrets file
- Rollback = `git revert` + `clawctl deploy push`
- Skills added by the agent get synced back as PRs — not silently applied
- The VPS is treated as replaceable compute; your state and config live in Git + backups

```
[Git repo]  ──push to main──►  [GitHub Actions]  ──SSH──►  [VPS]
    ▲                                                           │
    │                                                           │
    └─────────────── skill-sync PR ◄─── sync-skills-pr.sh ─────┘
```

---

## 2. What Lives in Git vs. What Stays on the VPS

| Item | Git? | Notes |
|------|------|-------|
| `docker-compose.yml` | ✅ Yes | Authoritative compose spec |
| `config/openclaw.json` | ✅ Yes | Model defaults, channels, tools |
| `config/SOUL.md` | ✅ Yes | Agent personality and rules |
| `config/HEARTBEAT.md` | ✅ Yes | Recurring agent tasks |
| `scripts/` | ✅ Yes | Bootstrap, backup, sync scripts |
| `skills/` | ✅ Yes | All custom and Hub-installed skills |
| `config/cloud-init.yaml` | ✅ Yes | VPS bootstrap automation |
| `.github/workflows/` | ✅ Yes | CI/CD pipelines |
| `.env` / `.env.production` | ❌ Never | Secrets — use a password manager |
| `.env.example` | ✅ Yes | Template with placeholder values |
| `/opt/openclaw/data/` | ❌ No | Runtime state, memory, agent data |
| `/opt/openclaw/workspace/` | ❌ No | Agent working directory |
| `/opt/openclaw/data/skills/` | Sync via PR | Agent-installed skills get PR'd back |

---

## 3. Recommended Repository Structure

Extend the existing `clawctl/` layout to support full GitOps:

```
clawctl/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml               ← Tests + linting on every PR
│   │   ├── deploy.yml           ← Auto-deploy to VPS on push to main
│   │   └── skill-sync.yml       ← Daily: detect and PR new skills from VPS
│   └── PULL_REQUEST_TEMPLATE.md
│
├── clawctl/                     ← Python CLI (unchanged)
│
├── config/
│   ├── openclaw.json            ← Agent configuration
│   ├── cloud-init.yaml          ← VPS bootstrap (canonical version)
│   ├── SOUL.md                  ← Agent personality/behaviour rules
│   └── HEARTBEAT.md             ← Recurring background tasks
│
├── docker/
│   ├── docker-compose.yml       ← Production (includes Watchtower)
│   └── docker-compose.dev.yml   ← Local dev overrides
│
├── scripts/
│   ├── bootstrap-vps.sh         ← First-time VPS setup
│   ├── backup.sh                ← rsync-based backup from VPS
│   ├── deploy.sh                ← Deploy wrapper (called by CI or manually)
│   └── sync-skills-pr.sh        ← Pull skills from VPS → open PR
│
├── skills/                      ← All skills live here
│   ├── README.md
│   └── my-custom-skill/
│       └── SKILL.md
│
├── .env.example
├── SPECS.md
├── OPENCLAW_TIPS.md
├── GITOPS_AND_MIGRATION.md      ← This file
└── pyproject.toml
```

---

## 4. GitHub Actions: CI and Auto-Deploy

### CI — runs on every PR

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v3
        with:
          version: "latest"

      - run: uv sync
      - run: uv run ruff check clawctl/
      - run: uv run mypy clawctl/
      - run: uv run pytest --cov=clawctl -v

      - name: Validate docker-compose
        run: docker compose -f docker/docker-compose.yml config --quiet

      - name: Validate openclaw.json
        run: python -c "import json; json.load(open('config/openclaw.json'))"
```

### Deploy — runs on push to main

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to VPS

on:
  push:
    branches: [main]
    paths:
      - 'docker/**'
      - 'config/**'
      - 'skills/**'
      - 'scripts/**'

jobs:
  deploy:
    runs-on: [self-hosted, vps]   # Self-hosted runner on the VPS (see below)
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Validate config
        run: |
          python -c "import json; json.load(open('config/openclaw.json'))"
          docker compose -f docker/docker-compose.yml config --quiet

      - name: Sync skills
        run: rsync -avz skills/ /opt/openclaw/data/skills/

      - name: Sync config
        run: |
          cp config/openclaw.json /opt/openclaw/data/config.json
          cp config/SOUL.md /opt/openclaw/data/SOUL.md || true
          cp config/HEARTBEAT.md /opt/openclaw/data/HEARTBEAT.md || true

      - name: Pull and restart container
        run: |
          cd /opt/openclaw
          docker compose -f /opt/clawctl/docker/docker-compose.yml pull
          docker compose -f /opt/clawctl/docker/docker-compose.yml up -d

      - name: Health check
        run: |
          sleep 10
          wget -qO- http://localhost:18789/health | grep -q '"status":"ok"'
          echo "Health check passed"
```

Store these secrets in GitHub → Settings → Secrets → Actions:

| Secret | Value |
|--------|-------|
| `GH_PAT` | Personal Access Token with `repo` scope (for skill-sync PRs) |

### Self-hosted runner on the VPS

Since OpenClaw ports bind to `127.0.0.1`, a GitHub-hosted runner cannot reach the
health endpoint. A self-hosted runner inside the Tailscale network solves this:

```bash
# On the VPS — set up GitHub Actions runner
mkdir -p /opt/actions-runner && cd /opt/actions-runner
curl -Lo runner.tar.gz \
  https://github.com/actions/runner/releases/download/v2.319.1/actions-runner-linux-x64-2.319.1.tar.gz
tar xzf runner.tar.gz

# Register (get token from: GitHub → Settings → Actions → Runners → New self-hosted runner)
./config.sh \
  --url https://github.com/<your-username>/clawctl \
  --token <RUNNER_TOKEN> \
  --name openclaw-vps \
  --labels vps,tailscale \
  --unattended

# Install and start as systemd service
sudo ./svc.sh install
sudo ./svc.sh start
```

The runner authenticates to GitHub over HTTPS (outbound) — no inbound ports needed.
It lives inside the Tailscale network and can reach `localhost:18789` directly.

---

## 5. Watchtower: Auto-Update Docker Images

Watchtower polls the container registry and restarts OpenClaw when a new image is
published — no manual `docker pull` required.

### Add to docker-compose.yml

```yaml
services:
  openclaw:
    # ... existing config ...

  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      WATCHTOWER_POLL_INTERVAL: 86400        # Check every 24 hours
      WATCHTOWER_CLEANUP: "true"             # Remove old images after update
      WATCHTOWER_MONITOR_ONLY: "false"       # Set "true" for notification-only mode
    command: openclaw                         # Only watch the openclaw container
```

### Pinned-version workflow (recommended for production)

Using `:latest` in production makes rollbacks impossible. The recommended pattern:

1. Pin the image version in `docker-compose.yml`:
   ```yaml
   image: ghcr.io/openclaw/openclaw:2026.2.25
   ```
2. Run Watchtower in **monitor-only** mode (`WATCHTOWER_MONITOR_ONLY: "true"`)
   so it notifies you (via Telegram/Slack) when a new image is available
3. You create a PR bumping the version tag — CI validates the compose file
4. Merge triggers GitHub Actions to deploy the pinned version

This gives you automatic update awareness with human review before deploy.

### Check for new image versions manually

```bash
# On the VPS
docker pull ghcr.io/openclaw/openclaw:latest
docker images ghcr.io/openclaw/openclaw
```

---

## 6. Skills as Code: Version Control & Deployment

All skills should live in the `skills/` directory in this repository. Skills
installed via `clawhub` on the VPS get pulled back into Git automatically.

### Directory layout

```
skills/
├── README.md                   ← How to add and review skills
├── my-custom-skill/
│   └── SKILL.md
├── perplexity-sonar/           ← ClawHub-installed skills land here too
│   └── SKILL.md
└── triple-memory/
    └── SKILL.md
```

### Manually deploy skills to the VPS

```bash
# Sync skills/ directory to VPS
rsync -avz skills/ root@openclaw-vps:/opt/openclaw/data/skills/

# Restart to pick up new skills
clawctl deploy restart
```

### Pull installed skills back from VPS

```bash
./scripts/sync-skills-pr.sh
```

This script detects what changed on the VPS and opens a PR for you to review before
the skill is considered permanent in Git.

---

## 7. OpenClaw Self-Modification: Auto-PR Workflow

This is the pattern that lets OpenClaw install and write skills autonomously while
keeping Git as the source of truth.

### Flow

```
OpenClaw installs/modifies a skill on VPS
            │
            ▼
sync-skills-pr.sh runs (daily via cron or GitHub Actions schedule)
            │
            ▼
Detects diff between /opt/openclaw/data/skills/ and skills/ in repo
            │
            ▼
Creates branch: skill-sync/YYYYMMDD-HHmmss
Commits changed SKILL.md files
Pushes and opens a PR via gh CLI
            │
            ▼
Human reviews: reads SKILL.md, checks for suspicious endpoints or exec calls
            │
            ▼
Merges PR → GitHub Actions deploys (idempotent if skills already on VPS)
```

### The sync script

Create `scripts/sync-skills-pr.sh`:

```bash
#!/usr/bin/env bash
# sync-skills-pr.sh — Pull skills from VPS and open a GitHub PR if anything changed
# Usage: VPS_HOST=openclaw-vps ./scripts/sync-skills-pr.sh
set -euo pipefail

VPS="${VPS_HOST:-openclaw-vps}"
REMOTE_SKILLS="/opt/openclaw/data/skills"
BRANCH="skill-sync/$(date +%Y%m%d-%H%M%S)"
REPO_SKILLS="./skills"

echo "=== Syncing skills from ${VPS}:${REMOTE_SKILLS} ==="
rsync -avz --delete "root@${VPS}:${REMOTE_SKILLS}/" "${REPO_SKILLS}/"

# Check for any changes (tracked or untracked under skills/)
CHANGED=$(git diff --name-only "${REPO_SKILLS}/" ; git ls-files --others --exclude-standard "${REPO_SKILLS}/")

if [ -z "${CHANGED}" ]; then
    echo "No skill changes detected. Nothing to PR."
    exit 0
fi

echo "Changed files:"
echo "${CHANGED}"

# Create branch, stage, commit, push, open PR
git checkout -b "${BRANCH}"
git add "${REPO_SKILLS}/"
git commit -m "chore(skills): sync from VPS — $(date +%Y-%m-%d)"
git push -u origin "${BRANCH}"

gh pr create \
  --title "Skills sync: $(date +%Y-%m-%d)" \
  --body "$(cat <<'EOF'
## Automated skills sync from VPS

OpenClaw installed or modified skills on the VPS. This PR captures those changes
for review before they become permanent in Git.

**Review checklist:**
- [ ] Each new/modified `SKILL.md` has been read and understood
- [ ] No unexpected third-party endpoints are referenced
- [ ] No suspicious `exec`, `bash`, or shell invocations without justification
- [ ] Required env vars are documented in the YAML frontmatter
- [ ] Skill source is listed on [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) or is custom-authored

Merge to make the VPS state the official record in Git.
EOF
)" \
  --label "skills,automated"

echo "PR opened from branch: ${BRANCH}"
```

Make it executable: `chmod +x scripts/sync-skills-pr.sh`

### Wire it up

**Option A: GitHub Actions scheduled workflow** (recommended)

Create `.github/workflows/skill-sync.yml`:

```yaml
name: Skill Sync

on:
  schedule:
    - cron: '0 7 * * *'    # Daily at 07:00 UTC
  workflow_dispatch:         # Manual trigger from GitHub UI

jobs:
  sync:
    runs-on: [self-hosted, vps]
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GH_PAT }}

      - name: Configure git
        run: |
          git config user.name "openclaw-bot"
          git config user.email "openclaw-bot@users.noreply.github.com"

      - name: Sync skills and open PR
        run: ./scripts/sync-skills-pr.sh
        env:
          VPS_HOST: localhost    # Runner is already on the VPS
          GH_TOKEN: ${{ secrets.GH_PAT }}
```

**Option B: cron job on your local machine**

```cron
# crontab -e — runs every morning at 07:00
0 7 * * * cd /path/to/clawctl && VPS_HOST=openclaw-vps ./scripts/sync-skills-pr.sh >> ~/.skill-sync.log 2>&1
```

### Teach the agent to trigger sync itself

Add to `config/SOUL.md` (or `config/openclaw.json` agent instructions):

```markdown
## Version Control Rules

After installing any new skill from ClawHub or writing a new custom skill,
run the following command to create a GitHub PR for human review:

    bash /opt/clawctl/scripts/sync-skills-pr.sh

Do NOT consider a skill permanent until its PR has been merged.
```

This closes the loop: the agent installs a skill, immediately opens a PR, and the
change is visible in GitHub before anyone has to remember to sync.

---

## 8. Migration Guide: Moving to a New VPS

Use this when:

- Migrating to a different Hetzner region (latency, data residency)
- Upgrading server type (CX33 → CX43)
- Recovering from a VPS failure or deletion
- Starting fresh with a cleaner setup

### Pre-migration: capture current state

```bash
# 1. Backup all VPS data to local machine
./scripts/backup.sh
# Creates: ./backups/YYYYMMDD_HHMMSS/{data,workspace}/

# 2. Sync any skills the agent installed directly to a PR
./scripts/sync-skills-pr.sh
# Review and merge (or just note the diff) before migrating

# 3. Export .env to your password manager (never to git)
ssh root@openclaw-vps 'cat /opt/openclaw/.env'
# → copy to 1Password / Bitwarden / Doppler

# 4. Note the exact running image
ssh root@openclaw-vps 'docker inspect openclaw --format "{{.Config.Image}}"'
# e.g.: ghcr.io/openclaw/openclaw:2026.2.25
```

### Step 1: Provision the new VPS

```bash
export HCLOUD_TOKEN="your-token"

# Upload SSH key (skip if already uploaded)
clawctl server ssh-key-upload

# Create new server — keep the old one running until cutover is verified
clawctl server create --name openclaw-vps-new --server-type cx33 --location nbg1

# Or with full cloud-init automation:
hcloud server create \
    --name openclaw-vps-new \
    --type cx33 \
    --image ubuntu-24.04 \
    --location nbg1 \
    --ssh-key openclaw-key \
    --user-data-from-file config/cloud-init.yaml
```

### Step 2: Bootstrap (skip if cloud-init was used)

```bash
NEW_IP=$(hcloud server ip --name openclaw-vps-new)
scp scripts/bootstrap-vps.sh root@${NEW_IP}:/tmp/
ssh root@${NEW_IP} bash /tmp/bootstrap-vps.sh
```

### Step 3: Connect Tailscale on the new VPS

```bash
ssh root@${NEW_IP} tailscale up --ssh
# → Authenticate in browser
# → Tailscale admin: disable key expiry for the new machine
```

### Step 4: Clone the clawctl repo on the new VPS

```bash
ssh root@${NEW_IP}
git clone https://github.com/<your-username>/clawctl.git /opt/clawctl
# This gives the new VPS access to all scripts and config
```

### Step 5: Restore data from backup

```bash
BACKUP_DIR="./backups/$(ls -t backups/ | head -1)"
NEW_VPS="root@$(tailscale ip --hostname openclaw-vps-new 2>/dev/null || echo ${NEW_IP})"

# Restore data and workspace
rsync -avz "${BACKUP_DIR}/data/"      ${NEW_VPS}:/opt/openclaw/data/
rsync -avz "${BACKUP_DIR}/workspace/" ${NEW_VPS}:/opt/openclaw/workspace/

# Fix permissions
ssh ${NEW_VPS} chown -R 1000:1000 /opt/openclaw/
```

### Step 6: Deploy OpenClaw

```bash
# Upload secrets and compose file, pull image, start container
clawctl deploy push \
    --host openclaw-vps-new \
    --compose-file docker/docker-compose.yml \
    --env-file .env.production

# Verify
clawctl status check  --host openclaw-vps-new
clawctl status doctor --host openclaw-vps-new
```

### Step 7: Verify before cutting over

```bash
# Test web UI through Tailscale
clawctl tunnel open --host openclaw-vps-new

# Check logs
clawctl deploy logs --host openclaw-vps-new --lines 50

# Send a test message to your Telegram bot — should respond normally
```

### Step 8: Cut over

**Option A: Rename the Tailscale machine**

In the Tailscale admin console: rename `openclaw-vps-new` → `openclaw-vps`.
MagicDNS name stays the same, SSH config stays the same, nothing else changes.

**Option B: Update SSH config**

```sshconfig
Host openclaw-vps
    HostName <new-tailscale-ip>
    User root
    IdentityFile ~/.ssh/openclaw_ed25519
    IdentitiesOnly yes
```

### Step 9: Update GitHub Actions

In GitHub → Settings → Secrets → Actions:
- Update `VPS_TAILSCALE_IP` to the new Tailscale IP (if used in workflows)
- Re-register the self-hosted runner on the new VPS:

```bash
# On new VPS — remove old runner registration first if needed
cd /opt/actions-runner
sudo ./svc.sh stop
./config.sh remove --token <RUNNER_TOKEN>

# Re-register pointing at new VPS
./config.sh \
  --url https://github.com/<your-username>/clawctl \
  --token <NEW_RUNNER_TOKEN> \
  --name openclaw-vps \
  --labels vps,tailscale \
  --unattended
sudo ./svc.sh install && sudo ./svc.sh start
```

### Step 10: Decommission the old VPS

Only after the new VPS has been running correctly for 24+ hours:

```bash
clawctl server destroy openclaw-vps
# Or: hcloud server delete openclaw-vps
```

> Hetzner charges by the hour — running both VPSes in parallel during migration
> costs ~€0.01/hour. Keep the old one until you're confident the new one is healthy.

---

## 9. Backup Strategy

### What to back up

| Data | Location on VPS | Frequency | Method |
|------|-----------------|-----------|--------|
| Agent memory, config | `/opt/openclaw/data/` | Daily | `scripts/backup.sh` |
| Agent workspace | `/opt/openclaw/workspace/` | Daily | `scripts/backup.sh` |
| Skills (runtime state) | `/opt/openclaw/data/skills/` | On change | `sync-skills-pr.sh` |
| Infrastructure config | Git repo | Continuous | Git commits |
| Secrets `.env` | Password manager | On change | Manual |

### Automated daily backup via cron

On your local machine:

```cron
# crontab -e
0 2 * * * cd /path/to/clawctl && ./scripts/backup.sh >> ~/.openclaw-backup.log 2>&1
```

### Backup to S3-compatible storage (optional)

Hetzner Object Storage is S3-compatible and costs ~€0.024/GB/mo. Extend
`scripts/backup.sh` to push completed backups offsite:

```bash
# Append to scripts/backup.sh after the rsync commands:
aws s3 sync ./backups/ s3://your-bucket/openclaw-backups/ \
    --delete \
    --endpoint-url https://nbg1.your-objectstorage.com \
    --region nbg1
```

### What you can always reconstruct from Git

If you have the Git repo + the `.env.production` file (from your password manager):

- The entire VPS bootstrap procedure (cloud-init.yaml, bootstrap-vps.sh)
- All Docker configuration (docker-compose.yml)
- All agent configuration (openclaw.json, SOUL.md, HEARTBEAT.md)
- All custom skills (skills/)
- The clawctl CLI tool itself

Agent memory and conversation history live only in `/opt/openclaw/data/` — back
those up regularly.

---

## 10. Disaster Recovery Checklist

Use this if you need to rebuild from scratch with no running VPS.

```
Pre-requisites:
[ ] Git repo cloned locally: git clone https://github.com/<you>/clawctl
[ ] .env.production retrieved from password manager
[ ] SSH key at ~/.ssh/openclaw_ed25519
[ ] HCLOUD_TOKEN set

Recovery steps (target: ~15 min):
[ ] clawctl server create --name openclaw-vps
[ ] Bootstrap: scp + ssh bootstrap-vps.sh OR use cloud-init
[ ] tailscale up --ssh on new VPS, disable key expiry in admin
[ ] Restore latest backup: rsync ./backups/LATEST/ → /opt/openclaw/
[ ] ssh root@new-vps: chown -R 1000:1000 /opt/openclaw/
[ ] git clone https://github.com/<you>/clawctl /opt/clawctl  (on VPS)
[ ] clawctl deploy push --env-file .env.production
[ ] clawctl status doctor
[ ] clawctl tunnel open — verify web UI loads
[ ] Send test message to Telegram bot — verify response
[ ] Update GitHub Actions secrets with new VPS IP
[ ] Re-register self-hosted runner on new VPS
[ ] Run sync-skills-pr.sh to reconcile any skill drift

Done. Agent is running.
```

---

## 11. Tricks & Tips

### Make clawctl available everywhere

```bash
# ~/.zshrc or ~/.bashrc
export CLAWCTL_DIR="$HOME/src/clawctl"
alias clawctl="uv run --project $CLAWCTL_DIR clawctl"
```

Any machine with `git clone` + `uv` can now manage your VPS.

### Tag stable baselines

```bash
git tag -a v1.0.0 -m "Stable OpenClaw + perplexity-sonar + triple-memory"
git push origin v1.0.0
```

Emergency rollback: `git checkout v1.0.0 -- config/ docker/ skills/ && clawctl deploy push`

### Pin the OpenClaw image to a digest (most reproducible)

```yaml
# docker-compose.yml
image: ghcr.io/openclaw/openclaw@sha256:abc123def456...
```

Get the current digest: `docker inspect ghcr.io/openclaw/openclaw:latest --format '{{index .RepoDigests 0}}'`

### Keep SOUL.md and HEARTBEAT.md in version control

OpenClaw uses these files to define agent personality and recurring tasks. Commit
them to `config/` and deploy them alongside `openclaw.json`. Changes to agent
behaviour should go through the same review process as code changes.

### Use GitHub Environments for staging vs. production

In GitHub → Settings → Environments:

- `production` — requires manual approval before deploy; secrets scoped here
- `staging` — auto-deploys; uses a local Docker instance or cheaper VPS

```yaml
# deploy.yml
jobs:
  deploy:
    environment: production    # Triggers manual approval gate in GitHub UI
```

### Quick health check alias

```bash
alias oc-health='clawctl status check && clawctl deploy logs --lines 20'
alias oc-sync='cd ~/src/clawctl && ./scripts/sync-skills-pr.sh'
```

### Validate everything before deploying

```bash
# Pre-deploy validation — run locally or in CI
python -c "import json; json.load(open('config/openclaw.json'))" && echo "JSON: OK"
docker compose -f docker/docker-compose.yml config --quiet && echo "Compose: OK"
uv run pytest --cov=clawctl -q && echo "Tests: OK"
```

### Secret rotation without downtime

```bash
# 1. Generate new token
NEW_TOKEN=$(openssl rand -hex 32)

# 2. Update .env.production
sed -i "s/OPENCLAW_GATEWAY_TOKEN=.*/OPENCLAW_GATEWAY_TOKEN=${NEW_TOKEN}/" .env.production

# 3. Push to VPS (clawctl restarts the container automatically)
clawctl deploy push --env-file .env.production

# 4. Update your password manager with the new token
```

### Clawctl on the VPS itself

For the skill-sync script to work from a self-hosted runner, clone the repo on the
VPS at a fixed path:

```bash
git clone https://github.com/<you>/clawctl /opt/clawctl
# Set up a deploy key so the VPS can pull (read-only):
ssh-keygen -t ed25519 -C "openclaw-vps-deploy" -f ~/.ssh/deploy_key -N ""
# Add the public key to GitHub → repo → Settings → Deploy keys (read-only)
```

Then keep it updated via the deploy workflow or a daily cron:

```bash
# /etc/cron.daily/clawctl-pull
#!/bin/bash
git -C /opt/clawctl pull origin main --ff-only
```

### Monitor for config drift

Add a step to your deploy workflow that alerts if the VPS has manual changes that
aren't in Git:

```bash
# Check if VPS skills differ from what's in the repo
ssh root@openclaw-vps "find /opt/openclaw/data/skills -name SKILL.md | sort" \
  > /tmp/vps-skills.txt
find skills -name SKILL.md | sort > /tmp/git-skills.txt
diff /tmp/git-skills.txt /tmp/vps-skills.txt && echo "No drift" || echo "Drift detected — run sync-skills-pr.sh"
```

---

*Last updated: 2026-02-28. Review after major OpenClaw releases or infrastructure changes.*
