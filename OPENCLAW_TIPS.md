# OpenClaw Tips & Tricks — Chief AI Engineer Edition

> Curated for a seasoned AI/SW engineer pivoting to Chief AI Engineer (privacy, governance) at a small consultancy.
> Focus: get productive fast, stay secure, stay defensible.
>
> Sources:
> - [OpenClaw Gateway Security docs](https://docs.openclaw.ai/gateway/security)
> - [Using OpenClaw AI Safely: Full Privacy & Security Guide — AtomicMail](https://atomicmail.io/blog/using-openclaw-ai-safely-full-privacy-security-guide)
> - [Running OpenClaw safely: identity, isolation, and runtime risk — Microsoft Security Blog](https://www.microsoft.com/en-us/security/blog/2026/02/19/running-openclaw-safely-identity-isolation-runtime-risk/)
> - [When AI Can Act: Governing OpenClaw — Cato Networks](https://www.catonetworks.com/blog/when-ai-can-act-governing-openclaw/)
> - [OpenClaw: Evolving Opportunities and Challenges Surrounding Agentic AI — Steptoe](https://www.steptoe.com/en/news-publications/steptechtoe-blog/openclaw-evolving-opportunities-and-challenges-surrounding-agentic-ai.html)
> - [OpenClaw Security: Risks of Exposed AI Agents — Bitsight](https://www.bitsight.com/blog/openclaw-ai-security-risks-exposed-instances)
> - [ClawSec: Hardening OpenClaw Agents from the Inside Out — SentinelOne](https://www.sentinelone.com/blog/clawsec-hardening-openclaw-agents-from-the-inside-out/)
> - [OpenClaw Sovereign AI Security Manifest — Penligent](https://www.penligent.ai/hackinglabs/openclaw-sovereign-ai-security-manifest-a-comprehensive-post-mortem-and-architectural-hardening-guide-for-openclaw-ai-2026/)
> - [What Security Teams Need to Know About OpenClaw — CrowdStrike](https://www.crowdstrike.com/en-us/blog/what-security-teams-need-to-know-about-openclaw-ai-super-agent/)
> - [ClawHub Skills registry](https://docs.openclaw.ai/tools/clawhub)
> - [Awesome OpenClaw Skills — VoltAgent/GitHub](https://github.com/VoltAgent/awesome-openclaw-skills)
> - [OpenClaw Capabilities Matrix — EastonDev](https://eastondev.com/blog/en/posts/ai/20260204-openclaw-capabilities-matrix/)
> - [SecureClaw (OWASP-aligned plugin) — Adversa AI/GitHub](https://github.com/adversa-ai/secureclaw)
> - [OpenClaw security vulnerabilities — Giskard](https://www.giskard.ai/knowledge/openclaw-security-vulnerabilities-include-data-leakage-and-prompt-injection-risks)

---

## Table of Contents

1. [Foundational Setup (Do These First)](#1-foundational-setup-do-these-first)
2. [Security Hardening](#2-security-hardening)
3. [Privacy Configuration](#3-privacy-configuration)
4. [Productive Workflow Automation](#4-productive-workflow-automation)
5. [ClawHub Skills — What to Install (and What to Avoid)](#5-clawhub-skills--what-to-install-and-what-to-avoid)
6. [Model Selection Strategy](#6-model-selection-strategy)
7. [AI Governance — Building Defensible Policies](#7-ai-governance--building-defensible-policies)
8. [Unsafe Setups to Avoid](#8-unsafe-setups-to-avoid)
9. [Maintenance & Incident Readiness](#9-maintenance--incident-readiness)
10. [Advanced / Power-User Moves](#10-advanced--power-user-moves)

---

## 1. Foundational Setup (Do These First)

- [ ] **Deploy on a dedicated, isolated VPS** — never your laptop or a shared dev box.
  Use `clawctl server create` to provision a Hetzner CX33 (~€5.49/month). Treat the VPS as untrusted compute; your secrets live elsewhere.

- [ ] **Enable Tailscale before exposing anything** — run `tailscale up --ssh` on the VPS immediately after bootstrap. All OpenClaw ports must bind to `127.0.0.1` only; Tailscale handles private routing.

- [ ] **Generate a strong gateway token** — use `openssl rand -hex 32` for `OPENCLAW_GATEWAY_TOKEN`. Never reuse tokens across environments (dev/staging/prod).

- [ ] **Set `dm_policy: pairing`** in `openclaw.json` for every Telegram (or other messaging) integration — never `open`. Approve pairings explicitly with `clawctl deploy pairing <CODE>`.

- [ ] **Define a `workspace/` sandbox boundary** — ensure the agent only reads/writes inside `/opt/openclaw/workspace/`. Never mount home directories or host OS paths into the container.

- [ ] **Configure UFW firewall** — allow only Tailscale interface traffic and port 22/TCP as SSH fallback. Block everything else at the cloud firewall level too (Hetzner Firewall rules).

- [ ] **Verify the deployment** — run `clawctl status doctor` and `clawctl status check` after every deploy. Fail fast; do not run a broken agent.

---

## 2. Security Hardening

- [ ] **Pin to a known-good OpenClaw image version** in `docker-compose.yml` (`image: openclaw/openclaw:2026.2.25` or later). Never use `:latest` in production — it makes rollbacks impossible and audits harder.

- [ ] **Update immediately when CVEs drop** — CVE-2026-25253 (WebSocket hijack granting shell access) hit in early 2026. Patch cadence for OpenClaw must be treated like OS security patches: apply within 24–48 h.

- [ ] **Install ClawSec (SentinelOne skill suite)** for prompt injection detection, supply chain integrity checks, and runtime behavior monitoring. It operates as a "skill-of-skills" and adds composable security layers without replacing existing skills. Install only from the official GitHub source.

- [ ] **Install SecureClaw (Adversa AI plugin)** for OWASP-aligned audit checks (56 checks, 5 hardening modules, 3 background monitors). Evaluate its 1,230-token context cost against your model budget — but the defense is worth it for client-facing deployments.

- [ ] **Enable exec approval gates** — configure OpenClaw to require explicit confirmation before executing any shell command. Hard enforcement beats system-prompt guardrails (which are soft guidance only).

- [ ] **Treat all inbound content as hostile** — links, email attachments, calendar invites, and pasted text are all indirect prompt injection (IPI) vectors. The 2026 ClawHavoc campaign embedded malicious instructions in calendar invites targeting active OpenClaw agents.

- [ ] **Use `known_hosts` host-key verification** — `clawctl`'s `ssh_utils.py` already loads system + user `known_hosts` instead of `AutoAddPolicy`. Never override this. Confirm no one has monkey-patched it in your fork.

- [ ] **Run Giskard automated red-teaming** periodically — adversarial probes cover prompt injection, tool-abuse, and cross-session leakage. Produce a report; file it as evidence in your governance portfolio.

---

## 3. Privacy Configuration

- [ ] **Set `DISABLE_TELEMETRY=1`** in your `.env` — execution can be local while telemetry, tokens, and logs still exfiltrate data to upstream vendors. Verify the flag is respected by checking outbound connections with `ss -tp` on the VPS.

- [ ] **Prefer a local or on-premises model** (e.g., Ollama + a quantised Qwen or Llama model) for any task involving client PII or confidential IP. Route to OpenRouter only for non-sensitive tasks.

- [ ] **Apply the Billboard Test before granting data access** — ask: "Would I be comfortable with this data on a public billboard?" If no, the agent must never see, touch, or remember it. Document this rule in your consultancy's AI use policy.

- [ ] **Audit `~/.openclaw/memory/` monthly** — delete any plaintext passwords, PII, or client data the agent may have memorised. Add a cron job to alert on files >100 KB in the memory directory (unusual growth often signals data retention anomalies).

- [ ] **Separate credentials by sensitivity tier** — use distinct API keys and tokens for client work vs. internal use. Store them in a secrets manager (Doppler, 1Password Secrets Automation) not in `.env` files checked into git.

- [ ] **Avoid connecting OpenClaw to OAuth scopes it doesn't need** — grant only the minimum required Gmail/Calendar/Slack scopes. Revoke and re-grant when scope needs change, so there's a clear audit trail.

- [ ] **Bind memory storage to the Tailscale private IP** — ensure the `/opt/openclaw/data/` volume is never exposed to the public internet and is included in encrypted backups (Hetzner Volume snapshots are sufficient for a consultancy scale).

---

## 4. Productive Workflow Automation

These are high-ROI automations for an AI governance consultant:

- [ ] **Daily brief via Telegram** — schedule a morning message with: today's calendar highlights, flagged client emails awaiting reply, overnight CI/CD failures (if applicable), and any new AI regulation news (EU AI Act updates, NIST AI RMF updates). One skill replaces five app-checks before coffee.

- [ ] **Email triage twice daily** — OpenClaw scans inbox, categorises by urgency, archives newsletters, flags action items with a one-line summary. Target: reduce inbox management from 30 min/day to 5 min/day.

- [ ] **Regulation tracker** — skill that monitors EU AI Act, NIST AI RMF, ISO 42001, and GDPR enforcement news via RSS/Brave search. Delivers a weekly digest. Essential for keeping client advice current.

- [ ] **Client deliverable drafting pipeline** — use a skill that: pulls the relevant framework (e.g., ISO 42001 clause), summarises recent enforcement precedents, and drafts a section outline. Human review and approval always remain mandatory before delivery.

- [ ] **GitHub / CI monitoring** — if maintaining client AI tools, route failed workflow alerts to Telegram with a diagnosis summary. Fix from your phone while mobile.

- [ ] **Meeting prep assistant** — 30 minutes before a scheduled meeting, OpenClaw summarises the last 5 email threads with that contact, pulls their company's recent news, and sends a brief to Telegram.

- [ ] **Skill update notification** — weekly `clawhub outdated` check run as a cron job; results delivered to Telegram. Never fall behind on security patches silently.

---

## 5. ClawHub Skills — What to Install (and What to Avoid)

### Install (vetted, high value)

- `file_search` — essential for navigating workspace documents; low risk.
- `web_search` (Brave) — research and regulation monitoring; prefer Brave over Google for privacy.
- `cron_scheduler` — powers all time-based automations; install early.
- `github_actions_monitor` — CI/CD failure alerts.
- `email_triage` — inbox management; review OAuth scope grants carefully.
- `calendar_brief` — daily schedule summary; grant read-only Calendar scope only.
- `rss_reader` — regulation tracker feeds; no auth required, very low risk.

### Evaluate carefully before installing

- Any skill requiring `browser` tool with stored session cookies — high IPI risk.
- Skills touching financial APIs — use a prepaid/virtual card API key; cap spending limits at the provider level.
- Multi-agent coordination skills — increased attack surface; test in isolation first.

### Avoid (red flags)

- Skills from authors with no GitHub history or <10 stars.
- Skills that request `exec` permissions without a documented reason.
- Skills that call undocumented third-party endpoints (check the `SKILL.md` carefully).
- Any skill not listed on [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) — it's a curated, filtered registry and a useful first filter.
- `bundled` skills auto-load if the matching CLI tool is installed — audit `skills.allowBundled` in whitelist mode and disable anything you don't explicitly need.

### Hygiene

- [ ] Run `clawhub list` monthly; uninstall anything unused (`clawhub uninstall <name>`).
- [ ] Check VirusTotal reports on ClawHub skill pages before first install.
- [ ] After installing a new skill, monitor agent logs for unexpected API calls for 48 h.

---

## 6. Model Selection Strategy

- [ ] **Use a frontier model for tool-using tasks** — Claude Sonnet 4.6 (`claude-sonnet-4-6`) or Claude Opus 4.6 (`claude-opus-4-6`) via OpenRouter. Smaller/cheaper models are more susceptible to prompt injection and instruction hijacking under adversarial inputs.

- [ ] **Default model in `openclaw.json`**: set to `anthropic/claude-sonnet-4-6` with a cost-efficient fallback (e.g., `moonshotai/kimi-k2-5` for non-sensitive summarisation tasks). Use `clawctl deploy configure-llm` to switch models without redeployment.

- [ ] **Use a local model (Ollama) for sensitive data** — route client PII or confidential documents through a local Qwen or Llama3 model. Never send regulated data to a third-party API without a DPA in place.

- [ ] **Document model choices in your governance log** — which model, which tasks, which data tiers. This is the foundation of your AI system inventory required under ISO 42001 and emerging EU AI Act obligations.

---

## 7. AI Governance — Building Defensible Policies

As a Chief AI Engineer with a governance remit, OpenClaw is both a tool and a case study. Use your own deployment to develop and demonstrate the policies you sell to clients.

- [ ] **Write an Agentic AI Use Policy** — most generative AI policies do not yet address autonomous agents. Your policy must explicitly cover: permitted/prohibited deployments, human-in-the-loop requirements (escalation triggers), approved tool scopes, data tiering rules, and how experimental-use approval is obtained.

- [ ] **Establish non-human identity (NHI) governance** — AI agents authenticate, store credentials, and take autonomous actions. Manage them with the same rigour as human accounts: unique service identities, scoped credentials, MFA-equivalent controls (the Tailscale mesh + gateway token is a good start), full audit trails.

- [ ] **Implement just-in-time (JIT) access for sensitive operations** — never leave long-lived credentials in the agent's reachable filesystem. Use a secrets manager that issues time-limited tokens on demand.

- [ ] **Establish an AI incident response runbook** — document: how to shut down the agent, wipe the workspace, revoke all third-party access, and rotate credentials. Test the runbook quarterly. Know your "kill switch."

- [ ] **Build an AI system inventory** — list every OpenClaw instance (yours + client), the model in use, data categories processed, and the risk tier. This is a prerequisite for ISO 42001 certification and EU AI Act Article 13 transparency obligations.

- [ ] **Run quarterly Giskard red-team sessions** — document findings, mitigations, and residual risk. File reports in your ISMS. This turns a security exercise into governance evidence.

- [ ] **Define data retention limits** — how long does OpenClaw memory persist? When is it wiped? Align with your GDPR retention schedule. Automate deletion via cron job; log deletions.

- [ ] **Create a client-facing AI transparency notice** — if you deploy OpenClaw for clients or use it to process client data, GDPR Article 13/14 likely requires disclosure. Draft a template notice covering: what the agent does, what data it processes, where data goes (model provider, Tailscale, Hetzner region), and how to opt out.

---

## 8. Unsafe Setups to Avoid

These are specifically dangerous given the 2026 threat landscape. Treat as hard rules.

- **Never expose OpenClaw's port to the public internet.** Over 40,000 instances were found exposed on Shodan in early 2026. Your Tailscale-only setup is correct; never bypass it "temporarily."

- **Never install skills without reading `SKILL.md` and reviewing source code.** The ClawHavoc campaign planted 341 malicious skills on ClawHub targeting credentials, crypto wallets, and API keys. VirusTotal integration on ClawHub is a first filter, not a guarantee.

- **Never use `dm_policy: open` on any Telegram bot.** Any Telegram user can then send arbitrary instructions to your agent. Use `pairing` always.

- **Never run OpenClaw on a shared dev machine or your personal laptop.** If an IPI attack succeeds, it has full access to everything on that machine.

- **Never store secrets in the agent's reachable memory.** If you've ever typed an API key, password, or token into the chat, assume it's in `~/.openclaw/memory/` — audit and delete immediately.

- **Never use a cheap/small LLM for tool-executing tasks.** Smaller models are measurably more susceptible to prompt injection. Save them for summarisation of non-sensitive text only.

- **Never skip the known_hosts check.** `AutoAddPolicy` in Paramiko is equivalent to ignoring SSL cert errors. It enables MITM attacks on every SSH session.

- **Never treat a system-prompt guardrail as a hard security control.** System prompts are soft guidance. Hard enforcement comes from: tool policy configuration, exec approval gates, sandbox isolation, and allowlists.

- **Never install bundled skills blindly.** Bundled skills auto-activate when their corresponding CLI tool is installed. Audit `skills.allowBundled` and use whitelist mode.

---

## 9. Maintenance & Incident Readiness

- [ ] **Weekly**: Run `clawhub outdated`; apply updates. Check `clawctl status doctor`. Review agent logs for anomalies.
- [ ] **Monthly**: Audit `~/.openclaw/memory/` for PII/credentials. Run `clawhub list` and uninstall unused skills. Rotate `OPENCLAW_GATEWAY_TOKEN`. Verify Tailscale ACLs are still correct.
- [ ] **Quarterly**: Run Giskard red-team probes. Test your incident response runbook end-to-end (shutdown → wipe → credential rotation → rebuild). Review and update your Agentic AI Use Policy.
- [ ] **On every CVE**: Update OpenClaw image immediately. Verify with `clawctl status check`. Document in your AI system inventory.

### Incident kill switch (memorise this sequence)
```bash
clawctl deploy restart          # Soft reset if agent is misbehaving
# If that's insufficient:
ssh root@<tailscale-ip> docker stop openclaw
ssh root@<tailscale-ip> docker rm openclaw
# Then rotate all credentials before redeploying:
# - OPENCLAW_GATEWAY_TOKEN
# - OPENROUTER_API_KEY
# - TELEGRAM_BOT_TOKEN
# - Any OAuth tokens granted to skills
clawctl deploy push --env-file .env.production  # Redeploy clean
```

---

## 10. Advanced / Power-User Moves

- [ ] **Publish your own governance skill to ClawHub** — a `regulation_tracker` or `gdpr_audit_checklist` skill is a reusable asset and a credibility signal for your consultancy. Build it against your own deployment first; publish once battle-tested.

- [ ] **Multi-agent coordination** — run a "researcher" agent (web_search + read) and a "drafter" agent (write) as separate OpenClaw instances on the same Tailscale network. File locks prevent workspace conflicts. Useful for generating client deliverables at scale.

- [ ] **Integrate with your ISMS** — if you use a GRC tool (e.g., Vanta, Drata, or a custom SharePoint), build a skill that auto-populates evidence tasks from OpenClaw outputs (red-team reports, memory audit logs). Reduces compliance admin significantly.

- [ ] **Use `clawctl deploy configure-llm`** to A/B test model performance on real governance tasks — compare Claude Sonnet 4.6 vs. a local Llama3-70B on regulation summarisation quality. Document results; this is also a client-facing data point.

- [ ] **Set up a staging OpenClaw instance** for testing new skills and model changes before promoting to the production deployment. Use a second Hetzner VPS or a local Docker environment. Never test untrusted skills on a production agent.

- [ ] **Build a `clawctl deploy onboard` template per client** — standardise which skills, which model, which data-tier rules apply. Version-control the templates. Onboarding a new client AI deployment becomes a 10-minute operation with full auditability.

---

*Last updated: 2026-02-28. Review quarterly or after any significant OpenClaw release.*
