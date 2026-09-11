"""`purplelab containment-check`: the mandatory pre-flight gate before any
detonation (docs/CONTAINMENT-AND-SAFETY.md rules 3 and 8). Every check fails
closed -- an error talking to a VM is treated as "containment not confirmed",
never as "probably fine".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import ssh, wazuh
from .config import Config

RunRemote = Callable[..., ssh.RemoteResult]


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def _check(name: str, run_remote: RunRemote, host, user, command: str, want_ok: bool, ok_detail: str, fail_detail: str) -> CheckResult:
    try:
        result = run_remote(host, user, command)
    except ssh.RemoteUnreachable as exc:
        return CheckResult(name, False, f"could not verify -- {exc}")

    passed = result.ok if want_ok else not result.ok
    return CheckResult(name, passed, ok_detail if passed else f"{fail_detail} (rc={result.returncode})")


def check_no_external_egress(config: Config, run_remote: RunRemote = ssh.run_remote) -> CheckResult:
    cmd = f"ping -c 1 -W 2 {config.external_probe_ip}"
    return _check(
        "victim-vm has no real internet egress",
        run_remote, config.victim_ssh_host, config.victim_ssh_user, cmd,
        want_ok=False,
        ok_detail=f"ping to {config.external_probe_ip} blocked, as expected",
        fail_detail=f"ping to {config.external_probe_ip} succeeded -- victim-vm can reach the real internet",
    )


def check_dns_via_sinkhole(config: Config, run_remote: RunRemote = ssh.run_remote) -> CheckResult:
    cmd = f"getent hosts {config.external_probe_domain} | awk '{{print $1}}'"
    try:
        result = run_remote(config.victim_ssh_host, config.victim_ssh_user, cmd)
    except ssh.RemoteUnreachable as exc:
        return CheckResult("victim-vm DNS resolves via the sinkhole", False, f"could not verify -- {exc}")

    resolved_ip = result.stdout.strip()
    if resolved_ip and resolved_ip == config.siem_vm_ip:
        return CheckResult("victim-vm DNS resolves via the sinkhole", True, f"{config.external_probe_domain} -> {resolved_ip} (siem-vm)")
    return CheckResult(
        "victim-vm DNS resolves via the sinkhole", False,
        f"{config.external_probe_domain} resolved to {resolved_ip or '(nothing)'}, expected siem-vm ({config.siem_vm_ip})",
    )


def check_wazuh_agent_connected(config: Config) -> CheckResult:
    try:
        status = wazuh.get_agent_status(config, config.victim_agent_name)
    except wazuh.WazuhConnectionError as exc:
        return CheckResult("Wazuh agent connected", False, f"could not verify -- {exc}")

    if status == "active":
        return CheckResult("Wazuh agent connected", True, "status: active")
    return CheckResult("Wazuh agent connected", False, f"status: {status or 'not found'}")


def check_kali_no_bridging(config: Config, run_remote: RunRemote = ssh.run_remote) -> CheckResult:
    cmd = (
        "sysctl -n net.ipv4.ip_forward; "
        "sysctl -n net.ipv6.conf.all.forwarding; "
        "sudo iptables -t nat -L -n | grep -c MASQUERADE || true"
    )
    try:
        result = run_remote(config.kali_ssh_host, config.kali_ssh_user, cmd)
    except ssh.RemoteUnreachable as exc:
        return CheckResult("kali-vm not bridging VMnet10 to the internet", False, f"could not verify -- {exc}")

    lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
    if len(lines) < 3:
        return CheckResult(
            "kali-vm not bridging VMnet10 to the internet", False,
            f"unexpected output verifying kali-vm network posture: {result.stdout!r}",
        )
    ipv4_forward, ipv6_forward, masquerade_rules = lines[0], lines[1], lines[2]
    ok = ipv4_forward == "0" and ipv6_forward == "0" and masquerade_rules == "0"
    detail = f"ip_forward={ipv4_forward} ip6_forward={ipv6_forward} masquerade_rules={masquerade_rules}"
    return CheckResult("kali-vm not bridging VMnet10 to the internet", ok, detail)


def run_all(config: Config, run_remote: RunRemote = ssh.run_remote) -> list[CheckResult]:
    return [
        check_no_external_egress(config, run_remote),
        check_dns_via_sinkhole(config, run_remote),
        check_wazuh_agent_connected(config),
        check_kali_no_bridging(config, run_remote),
    ]
