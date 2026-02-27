#!/usr/bin/env bash
# bootstrap-vps.sh — First-time VPS setup: Docker + Tailscale + UFW + OpenClaw dirs
# Run as root on a fresh Ubuntu 24.04 VPS:
#   scp scripts/bootstrap-vps.sh root@<IP>:/tmp/
#   ssh root@<IP> bash /tmp/bootstrap-vps.sh
set -euo pipefail

echo "=== Updating system packages ==="
apt update && apt upgrade -y

echo "=== Installing Docker ==="
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
docker --version

echo "=== Installing Tailscale ==="
curl -fsSL https://tailscale.com/install.sh | sh
echo ""
echo ">>> ACTION REQUIRED: run the following to authenticate Tailscale:"
echo "    tailscale up --ssh"
echo "    Then open the printed URL, approve the device, and disable key expiry."
echo ""

echo "=== Configuring UFW firewall ==="
ufw default deny incoming
ufw default allow outgoing
ufw allow in on tailscale0   # All Tailscale traffic
ufw allow 22/tcp              # SSH fallback on public IP
ufw --force enable
ufw status verbose

echo "=== Creating OpenClaw directories ==="
mkdir -p /opt/openclaw/data /opt/openclaw/workspace
chown -R 1000:1000 /opt/openclaw/data /opt/openclaw/workspace
ls -la /opt/openclaw/

echo ""
echo "=== Bootstrap complete! ==="
echo "Next: run 'tailscale up --ssh', then deploy with 'clawctl deploy push'"
