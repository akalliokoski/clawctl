# OpenClaw Agent — Heartbeat Tasks

Recurring background tasks that OpenClaw should perform automatically.

## Daily Tasks

### Health Self-Check
- **Schedule:** Every morning
- **Action:** Verify all configured tools and integrations are working
- **On failure:** Notify the owner via Telegram with the error details

### Skill Inventory
- **Schedule:** Daily
- **Action:** List all installed skills and confirm they load without errors
- **On failure:** Report which skills failed to load and why

## Weekly Tasks

### Workspace Cleanup
- **Schedule:** Weekly (Sunday)
- **Action:** Review workspace for stale temporary files older than 7 days
- **Action:** Summarize disk usage and report if approaching capacity

## On-Demand Tasks

These run in response to events, not on a schedule:

### Post-Skill-Install Sync
- **Trigger:** After installing or modifying any skill
- **Action:** Run `bash /opt/clawctl/scripts/sync-skills-pr.sh` to open a PR
- **Purpose:** Keep Git as the source of truth for all skills
