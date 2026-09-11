"""Wraps VMware Workstation's `vmrun` CLI so `purplelab detonate` can revert
victim-vm to its clean-baseline snapshot itself, rather than trusting it was
done by hand. `vmrun` ships with VMware Workstation/Player.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

# Common Windows install locations, checked if `vmrun` isn't already on PATH.
_CANDIDATE_PATHS = [
    r"C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe",
    r"C:\Program Files\VMware\VMware Workstation\vmrun.exe",
]


class VmrunError(RuntimeError):
    pass


def find_vmrun() -> str:
    found = shutil.which("vmrun")
    if found:
        return found
    for candidate in _CANDIDATE_PATHS:
        if Path(candidate).exists():
            return candidate
    raise VmrunError(
        "`vmrun` not found on PATH or in the usual VMware Workstation install locations. "
        "Add it to PATH, or run the revert manually in the VMware GUI before detonating."
    )


def _run(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    vmrun = find_vmrun()
    proc = subprocess.run([vmrun, "-T", "ws", *args], capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise VmrunError(f"vmrun {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc


def revert_to_snapshot(vmx_path: str, snapshot_name: str) -> None:
    _run(["revertToSnapshot", vmx_path, snapshot_name])


def start(vmx_path: str) -> None:
    _run(["start", vmx_path, "nogui"])


def list_snapshots(vmx_path: str) -> list[str]:
    proc = _run(["listSnapshots", vmx_path])
    lines = proc.stdout.splitlines()[1:]  # first line is a "Total snapshots: N" header
    return [l.strip() for l in lines if l.strip()]
