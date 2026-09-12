#!/usr/bin/env bash
# The safety-critical part of kali-vm provisioning, factored out so it can
# be re-run on its own (`make kali-verify`) without redoing tooling checks.
# See docs/CONTAINMENT-AND-SAFETY.md rule 8. Fails loudly (non-zero exit) on
# any bad posture -- never continues past a check it can't confirm.

set -euo pipefail

fail() {
    echo ""
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "! $1"
    echo "! Refusing to continue -- fix this before using kali-vm."
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    exit 1
}

iface_count="$(ip -o link show | awk -F': ' '{print $2}' | grep -vc '^lo$')"
echo "non-loopback interfaces: $iface_count"
if [ "$iface_count" -ne 2 ]; then
    fail "kali-vm must have EXACTLY 2 network adapters (VMnet10 + NAT); found $iface_count. See docs/VM-BUILD-RUNBOOK.md step 4."
fi

sudo sysctl -w net.ipv4.ip_forward=0 >/dev/null
sudo sysctl -w net.ipv6.conf.all.forwarding=0 >/dev/null

persist_file="/etc/sysctl.d/99-vanta-no-forward.conf"
if [ ! -f "$persist_file" ]; then
    sudo tee "$persist_file" >/dev/null <<'EOF'
# Vanta: kali-vm must never forward traffic between VMnet10 and its NAT
# adapter -- that would bridge the isolated lab network to the real
# internet. See docs/CONTAINMENT-AND-SAFETY.md rule 8.
net.ipv4.ip_forward = 0
net.ipv6.conf.all.forwarding = 0
EOF
fi

ipv4_forward="$(sysctl -n net.ipv4.ip_forward)"
ipv6_forward="$(sysctl -n net.ipv6.conf.all.forwarding)"
echo "net.ipv4.ip_forward=$ipv4_forward net.ipv6.conf.all.forwarding=$ipv6_forward"
[ "$ipv4_forward" = "0" ] || fail "net.ipv4.ip_forward did not stick at 0 (got $ipv4_forward)"
[ "$ipv6_forward" = "0" ] || fail "net.ipv6.conf.all.forwarding did not stick at 0 (got $ipv6_forward)"

masquerade_rules="$(sudo iptables -t nat -L -n 2>/dev/null | grep -c MASQUERADE || true)"
echo "MASQUERADE rules in iptables -t nat: $masquerade_rules"
if [ "$masquerade_rules" -ne 0 ]; then
    fail "found $masquerade_rules MASQUERADE rule(s) in iptables -t nat -- this could bridge VMnet10 to the internet. Remove them by hand and re-run."
fi

echo "network posture OK: 2 interfaces, forwarding off, no masquerade rules"
