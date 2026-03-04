---
name: my-custom-skill
version: 1.0.0
description: Template for a custom OpenClaw skill
author: your-name
requires:
  env: []
  binaries: []
tags: [template, example]
---

# My Custom Skill

This is a template for a custom OpenClaw skill. Replace this content with your
actual skill implementation.

## What this skill does

Describe what this skill enables the agent to do.

## Configuration

No additional configuration required.

## Usage

Ask the agent to use this skill by describing the task naturally:

> "Use my-custom-skill to..."

## Notes

- Skills live in `~/.openclaw/skills/<skill-name>/SKILL.md`
- They are auto-loaded on startup
- Required env vars listed in frontmatter gate skill availability
- See https://docs.openclaw.ai/skills for the full skill authoring guide
