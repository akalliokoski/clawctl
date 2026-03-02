#!/usr/bin/env bash
# sync-skills-pr.sh — Pull skills from VPS and open a GitHub PR if anything changed
# Usage: VPS_HOST=openclaw-vps ./scripts/sync-skills-pr.sh
set -euo pipefail

VPS="${VPS_HOST:-openclaw-vps}"
REMOTE_SKILLS="/opt/openclaw/data/skills"
BRANCH="skill-sync/$(date +%Y%m%d-%H%M%S)"
REPO_SKILLS="./skills"

echo "=== Syncing skills from ${VPS}:${REMOTE_SKILLS} ==="
if [ "$VPS" = "localhost" ]; then
    rsync -av --delete "${REMOTE_SKILLS}/" "${REPO_SKILLS}/"
else
    rsync -avz --delete "root@${VPS}:${REMOTE_SKILLS}/" "${REPO_SKILLS}/"
fi

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
