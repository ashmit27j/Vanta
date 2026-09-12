#!/usr/bin/env bash
# Provisions kali-vm: confirms attack tooling, and -- more importantly --
# verifies and enforces the network posture that makes kali-vm's second
# (NAT) adapter safe to have at all (docs/CONTAINMENT-AND-SAFETY.md rule 8,
# checked by verify-network.sh in this directory).
#
# This is deliberately NOT a "build a custom toolset" script -- kali-vm ships
# with Metasploit/Nmap/etc. already; this just confirms they're present and
# up to date. The network check fails loudly (non-zero exit) rather than
# continuing on a bad posture.
#
# Idempotent. Run this INSIDE kali-vm, not on the Windows host.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

REPO_DIR="${REPO_DIR:-$HOME/Vanta}"
CONFIG_FILE="$REPO_DIR/tooling/config.yaml"

echo "==> [1/3] Attack tooling (verify/update, not a custom install)"
sudo apt-get update -y
for pkg in metasploit-framework nmap; do
    if dpkg -s "$pkg" >/dev/null 2>&1; then
        echo "    $pkg: present"
    else
        echo "    $pkg: NOT FOUND -- installing (unexpected on stock Kali)"
        sudo apt-get install -y "$pkg"
    fi
done

echo "==> [2/3] Network posture (the safety-critical part)"
bash "$SCRIPT_DIR/verify-network.sh"

echo "==> [3/3] Repo + expected IPs"
if [ ! -d "$REPO_DIR" ]; then
    echo "    $REPO_DIR not found -- clone the repo there first (see docs/VM-BUILD-RUNBOOK.md), then re-run."
    exit 1
fi
(cd "$REPO_DIR" && git pull --ff-only) || echo "    (git pull failed/skipped -- not fatal, continuing)"

if [ -f "$CONFIG_FILE" ]; then
    siem_ip="$(grep -E '^siem_vm_ip:' "$CONFIG_FILE" | sed -E 's/^siem_vm_ip:\s*"?([^"[:space:]]*)"?.*/\1/')"
    victim_ip="$(grep -E '^#?\s*victim_ssh_host:' "$CONFIG_FILE" | sed -E 's/^#?\s*victim_ssh_host:\s*"?([^"[:space:]]*)"?.*/\1/')"
    echo "    siem-vm (from tooling/config.yaml):   ${siem_ip:-<not set>}"
    echo "    victim-vm (from tooling/config.yaml): ${victim_ip:-<not set, or still commented out>}"
else
    echo "    $CONFIG_FILE not found -- fill in tooling/config.yaml (see tooling/README.md) to see expected IPs here."
fi

echo ""
echo "kali-vm provisioned. Re-run 'make kali-verify' any time to re-check network posture"
echo "without redoing the tooling checks."
