"""`purplelab detonate`: the guided, safety-gated real-sample workflow
(docs/prompt-chain.md Prompt 8, docs/CONTAINMENT-AND-SAFETY.md). Refuses to
proceed if any gate fails. See CONTAINMENT-AND-SAFETY.md for the sample
sources (MalwareBazaar, theZoo) and handling rules this enforces.

The sample itself must already be on victim-vm (downloaded there directly,
per CONTAINMENT-AND-SAFETY.md rule 5/6) -- `sample_path` below is a path on
victim-vm, never on the host.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from . import containment, ssh, vmrun, wazuh
from .config import Config

CLEAN_SNAPSHOT_NAME = "clean-baseline"
DEFAULT_WINDOW_SECONDS = 300
SSH_WAIT_RETRIES = 12
SSH_WAIT_INTERVAL_SECONDS = 5


class DetonationAborted(RuntimeError):
    """Raised when a safety gate fails -- always caught at the CLI layer and
    turned into a clean non-zero exit, never a stack trace.
    """


@dataclass
class DetonationResult:
    sample_path: str
    sample_sha256: str
    started_at: str
    ended_at: str
    evidence_dir: str
    containment_checks: list[dict] = field(default_factory=list)


def _wait_for_ssh(config: Config, run_remote, sleep_fn) -> None:
    for attempt in range(SSH_WAIT_RETRIES):
        try:
            result = run_remote(config.victim_ssh_host, config.victim_ssh_user, "echo ready")
            if result.ok:
                return
        except ssh.RemoteUnreachable:
            pass
        sleep_fn(SSH_WAIT_INTERVAL_SECONDS)
    raise DetonationAborted(f"victim-vm wasn't reachable over SSH after {SSH_WAIT_RETRIES} attempts")


def _revert_clean(config: Config, vmrun_mod) -> None:
    if not config.victim_vmx_path:
        raise DetonationAborted(
            "victim_vmx_path isn't configured -- can't confirm/perform the clean-baseline revert. "
            "Set it in tooling/config.yaml, or revert by hand in VMware and re-run."
        )
    try:
        vmrun_mod.revert_to_snapshot(config.victim_vmx_path, CLEAN_SNAPSHOT_NAME)
    except vmrun_mod.VmrunError as exc:
        raise DetonationAborted(f"could not revert victim-vm to '{CLEAN_SNAPSHOT_NAME}': {exc}") from exc

    try:
        vmrun_mod.start(config.victim_vmx_path)
    except vmrun_mod.VmrunError:
        pass  # commonly "already powered on" depending on snapshot power state -- not fatal


def _run_containment_gate(config: Config, run_remote) -> list[containment.CheckResult]:
    results = containment.run_all(config, run_remote)
    failing = [r for r in results if not r.passed]
    if failing:
        detail = "; ".join(f"{r.name}: {r.detail}" for r in failing)
        raise DetonationAborted(f"containment check failed -- {detail}")
    return results


def _sample_hash(config: Config, run_remote, sample_path: str) -> str:
    result = run_remote(config.victim_ssh_host, config.victim_ssh_user, f"sha256sum {sample_path}")
    if not result.ok or not result.stdout.strip():
        raise DetonationAborted(f"could not hash {sample_path} on victim-vm: {result.stderr.strip()}")
    return result.stdout.split()[0]


def _collect(run_remote, host, user, command: str) -> str:
    try:
        result = run_remote(host, user, command)
        return result.stdout if result.ok else f"(command failed, rc={result.returncode}: {result.stderr.strip()})"
    except ssh.RemoteUnreachable as exc:
        return f"(unavailable: {exc})"


def run_detonation(
    config: Config,
    sample_path: str,
    exec_cmd: str | None = None,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    run_remote: Callable = ssh.run_remote,
    vmrun_mod=vmrun,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> DetonationResult:
    # Gate 1: confirmed clean revert (docs/CONTAINMENT-AND-SAFETY.md rule 1)
    _revert_clean(config, vmrun_mod)
    _wait_for_ssh(config, run_remote, sleep_fn)

    # Gate 2: containment intact (rules 3, 8)
    checks = _run_containment_gate(config, run_remote)

    # Sample hash, recorded before detonation (rule: hash tied to evidence)
    sample_hash = _sample_hash(config, run_remote, sample_path)

    started_at = datetime.now(timezone.utc)
    exec_cmd = exec_cmd or sample_path
    try:
        run_remote(config.victim_ssh_host, config.victim_ssh_user, exec_cmd, timeout=30)
    except ssh.RemoteUnreachable:
        pass  # a timed-out/backgrounded sample is expected, not an error here

    sleep_fn(window_seconds)
    ended_at = datetime.now(timezone.utc)

    evidence_dir = (
        config.repo_root / "journal" / "evidence" / f"{started_at.strftime('%Y%m%dT%H%M%SZ')}-{sample_hash[:12]}"
    )
    evidence_dir.mkdir(parents=True, exist_ok=True)

    since_journalctl = started_at.strftime("%Y-%m-%d %H:%M:%S")
    (evidence_dir / "audit.log").write_text(
        _collect(run_remote, config.victim_ssh_host, config.victim_ssh_user, "sudo ausearch -ts recent -i")
    )
    (evidence_dir / "sysmon.log").write_text(
        _collect(
            run_remote, config.victim_ssh_host, config.victim_ssh_user,
            f'journalctl -u sysmon --since "{since_journalctl}" --no-pager -o json',
        )
    )
    (evidence_dir / "inetsim.log").write_text(
        _collect(run_remote, config.siem_vm_ip, config.siem_ssh_user, "sudo tail -n 500 /var/log/inetsim/service.log")
    )

    try:
        alerts = wazuh.search_alerts(config, config.victim_agent_name, since=started_at, until=ended_at)
        (evidence_dir / "wazuh_alerts.json").write_text(
            json.dumps([a.__dict__ for a in alerts], indent=2)
        )
    except wazuh.WazuhConnectionError as exc:
        (evidence_dir / "wazuh_alerts.json").write_text(json.dumps({"error": str(exc)}))

    result = DetonationResult(
        sample_path=sample_path,
        sample_sha256=sample_hash,
        started_at=started_at.isoformat(),
        ended_at=ended_at.isoformat(),
        evidence_dir=str(evidence_dir),
        containment_checks=[{"name": c.name, "passed": c.passed, "detail": c.detail} for c in checks],
    )
    (evidence_dir / "manifest.json").write_text(json.dumps(result.__dict__, indent=2))
    return result
