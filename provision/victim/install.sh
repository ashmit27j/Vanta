#!/usr/bin/env bash
# Provisions victim-vm (Ubuntu Desktop): Wazuh agent, auditd + a strong
# ruleset, Sysmon-for-Linux, PowerShell + Invoke-AtomicRedTeam, and a
# locked-down samples working directory.
#
# Idempotent: safe to re-run after a partial failure or on an
# already-provisioned box. Run this INSIDE victim-vm, not on the Windows
# host, and only after confirming victim-vm has no real internet route
# (see docs/CONTAINMENT-AND-SAFETY.md) -- this script itself needs outbound
# access to package repos during the initial build, before isolation is
# what you're relying on for safety; do this provisioning BEFORE detonating
# anything, on a VM that at this stage may still be behind normal NAT for
# setup, then switch its adapter to VMnet10-only per VM-BUILD-RUNBOOK.md.
#
# Required: SIEM_MANAGER_IP env var (siem-vm's IP on VMnet10).

set -euo pipefail

: "${SIEM_MANAGER_IP:?Set SIEM_MANAGER_IP to the siem-vm IP, e.g. SIEM_MANAGER_IP=192.168.110.10 ./install.sh}"
AGENT_NAME="${AGENT_NAME:-victim-vm}"
WAZUH_VERSION_LINE="${WAZUH_VERSION_LINE:-4.x}"  # matches the Wazuh apt repo's release line, not a specific patch version
SYSMON_VERSION="${SYSMON_VERSION:-1.0.0}"

echo "==> [1/5] Wazuh agent"
if ! dpkg -s wazuh-agent >/dev/null 2>&1; then
    curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | \
        sudo gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import
    sudo chmod 644 /usr/share/keyrings/wazuh.gpg
    echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/${WAZUH_VERSION_LINE}/apt/ stable main" | \
        sudo tee /etc/apt/sources.list.d/wazuh.list >/dev/null
    sudo apt-get update -y
    WAZUH_MANAGER="$SIEM_MANAGER_IP" WAZUH_AGENT_NAME="$AGENT_NAME" sudo -E apt-get install -y wazuh-agent
else
    echo "    wazuh-agent already installed -- ensuring manager IP is correct"
    sudo sed -i "s/<address>.*<\/address>/<address>${SIEM_MANAGER_IP}<\/address>/" /var/ossec/etc/ossec.conf
fi
sudo systemctl daemon-reload
sudo systemctl enable wazuh-agent
sudo systemctl restart wazuh-agent

echo "==> [2/5] auditd + ruleset"
sudo apt-get install -y auditd audispd-plugins
sudo cp "$(dirname "$0")/audit.rules" /etc/audit/rules.d/vanta.rules
sudo augenrules --load
sudo systemctl enable auditd
sudo systemctl restart auditd

echo "==> [3/5] Sysmon-for-Linux"
if ! command -v sysmon >/dev/null 2>&1; then
    tmp_deb="$(mktemp --suffix=.deb)"
    # Microsoft's own packages repo -- same one used for PowerShell below.
    wget -q "https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/packages-microsoft-prod.deb" -O /tmp/packages-microsoft-prod.deb
    sudo dpkg -i /tmp/packages-microsoft-prod.deb
    sudo apt-get update -y
    sudo apt-get install -y sysmonforlinux
    rm -f "$tmp_deb"
else
    echo "    sysmon already installed"
fi
# -accepteula required non-interactively; -i (re-)installs the driver+config and (re)starts the service.
sudo sysmon -accepteula -i "$(dirname "$0")/sysmon-config.xml"

echo "==> [4/5] PowerShell + Invoke-AtomicRedTeam"
if ! command -v pwsh >/dev/null 2>&1; then
    # packages-microsoft-prod.deb already added above (Sysmon step) covers this repo too.
    sudo apt-get update -y
    sudo apt-get install -y powershell
else
    echo "    pwsh already installed"
fi

if [ ! -d "$HOME/AtomicRedTeam" ]; then
    pwsh -NoProfile -Command "
        IEX (IWR 'https://raw.githubusercontent.com/redcanaryco/invoke-atomicredteam/master/install-atomicredteam.ps1' -UseBasicParsing);
        Install-AtomicRedTeam -getAtomics -Force
    "
else
    echo "    ~/AtomicRedTeam already present -- not reinstalling"
fi

echo "==> [5/5] Locked-down samples directory"
mkdir -p "$HOME/samples"
chmod 700 "$HOME/samples"

echo ""
echo "========================================================================"
echo " SAFETY REMINDERS (see docs/CONTAINMENT-AND-SAFETY.md)"
echo "   - Never mount host shared folders on this VM during detonation."
echo "   - Never put real credentials on this VM."
echo "   - Snapshot this VM as 'clean-baseline' now, before running anything."
echo "   - Verify no real internet route BEFORE detonating -- run"
echo "     'purplelab containment-check' from the host once tooling/config.yaml"
echo "     is filled in."
echo "========================================================================"
