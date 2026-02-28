# Skills

All OpenClaw skills live in this directory. Skills installed via ClawHub on the
VPS are synced back here automatically via `scripts/sync-skills-pr.sh`.

## Directory Layout

```
skills/
├── README.md                   ← This file
├── my-custom-skill/
│   └── SKILL.md
├── perplexity-sonar/           ← ClawHub-installed skills land here too
│   └── SKILL.md
└── triple-memory/
    └── SKILL.md
```

## Adding a New Skill

1. Create a directory under `skills/` with the skill name
2. Add a `SKILL.md` file with YAML frontmatter and skill instructions
3. Open a PR for review
4. After merge, the deploy workflow syncs skills to the VPS

## Skill File Format

```markdown
---
name: skill-name
version: 1.0.0
description: What this skill does
author: your-name
requires:
  env: [API_KEY_NAME]
  binaries: []
tags: [category]
---

# Skill Name

Instructions for the agent on how to use this skill.
```

## Reviewing Skills

Before approving a skill PR, check:

- [ ] `SKILL.md` has been read and the instructions are understood
- [ ] No unexpected third-party endpoints are referenced
- [ ] No suspicious `exec`, `bash`, or shell invocations without justification
- [ ] Required env vars are documented in the YAML frontmatter
- [ ] Skill source is listed on [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) or is custom-authored

## Deploying Skills Manually

```bash
# Sync skills/ directory to VPS
rsync -avz skills/ root@openclaw-vps:/opt/openclaw/data/skills/

# Restart to pick up new skills
clawctl deploy restart
```

## Pulling Skills from VPS

```bash
./scripts/sync-skills-pr.sh
```

This detects changes on the VPS and opens a PR for review.
