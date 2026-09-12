#!/usr/bin/env bash
# Installs INetSim (fake-internet sinkhole) on siem-vm: answers DNS and
# HTTP/HTTPS for any request with canned responses and logs everything, so
# victim-vm's detonation traffic has somewhere to go that isn't the real
# internet. See docs/CONTAINMENT-AND-SAFETY.md and docs/ARCHITECTURE.md.
#
# CAVEAT: INetSim ships as a Debian/Kali apt package, but not in default
# Ubuntu repos, and its Perl build dependencies vary by release. This
# installs from the official source tarball (inetsim.org), which is the
# most version-portable method, but the exact Perl module list below is
# best-effort -- if `inetsim --check` (run at the end) reports missing
# modules, install them with `sudo apt install libmodule-name-perl` and
# re-run this script (idempotent).
#
# Run this INSIDE siem-vm, after provision/siem/install.sh (Wazuh).

set -euo pipefail

INETSIM_VERSION="${INETSIM_VERSION:-1.3.2}"
INETSIM_DIR="${INETSIM_DIR:-/opt/inetsim}"
SIEM_IP="${SIEM_IP:-$(hostname -I | awk '{print $1}')}"

echo "==> Installing INetSim's Perl dependencies"
sudo apt-get update -y
sudo apt-get install -y \
    libnet-server-perl libnet-dns-perl libnet-libidn-perl \
    libio-socket-ssl-perl libipc-shareable-perl libdigest-sha-perl \
    libdatetime-perl libdatetime-format-strptime-perl libyaml-perl \
    perl-modules

if [ ! -d "$INETSIM_DIR" ]; then
    echo "==> Downloading INetSim ${INETSIM_VERSION}"
    tmp_dir="$(mktemp -d)"
    curl -fsSL "https://www.inetsim.org/downloads/inetsim-${INETSIM_VERSION}.tar.gz" -o "$tmp_dir/inetsim.tar.gz"
    tar -xzf "$tmp_dir/inetsim.tar.gz" -C "$tmp_dir"
    sudo mv "$tmp_dir/inetsim-${INETSIM_VERSION}" "$INETSIM_DIR"
    rm -rf "$tmp_dir"
else
    echo "==> $INETSIM_DIR already exists -- not re-downloading."
fi

echo "==> Pointing INetSim's sinkhole responses at siem-vm's own IP ($SIEM_IP)"
conf="$INETSIM_DIR/conf/inetsim.conf"
sudo cp -n "$conf" "$conf.orig" 2>/dev/null || true  # keep a pristine copy on first run only

sudo sed -i \
    -e "s/^#\?dns_default_ip.*/dns_default_ip $SIEM_IP/" \
    -e "s/^#\?service_bind_address.*/service_bind_address $SIEM_IP/" \
    "$conf"

# Make sure dns, http, https are in the enabled service list -- INetSim's
# default config already enables these, but assert it rather than assume.
for svc in dns http https; do
    grep -qE "^start_service\s+$svc" "$conf" || echo "start_service $svc" | sudo tee -a "$conf" >/dev/null
done

echo "==> Verifying the install"
sudo "$INETSIM_DIR/inetsim" --check || {
    echo ""
    echo "INetSim reported missing dependencies above -- install them (apt install libX-perl)"
    echo "and re-run this script. It's idempotent."
    exit 1
}

echo "==> Installing the systemd unit (so INetSim runs as a daemon, not a foreground process)"
unit_path="/etc/systemd/system/inetsim.service"
sudo tee "$unit_path" >/dev/null <<EOF
[Unit]
Description=INetSim fake-internet sinkhole
After=network.target

[Service]
Type=simple
ExecStart=$INETSIM_DIR/inetsim
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable inetsim
sudo systemctl restart inetsim

echo ""
echo "INetSim installed at $INETSIM_DIR, configured to answer as $SIEM_IP, running as a systemd service."
echo "Check it with: systemctl status inetsim / journalctl -u inetsim -f"
echo ""
echo "Next: point victim-vm's DNS and default route at $SIEM_IP (see docs/VM-BUILD-RUNBOOK.md and"
echo "provision/victim/install.sh), then verify with 'purplelab containment-check' from victim-vm."
