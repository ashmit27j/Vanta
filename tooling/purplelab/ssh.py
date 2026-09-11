"""Thin wrapper around the system `ssh` client for running commands on
victim-vm / kali-vm from the host. Exists mainly so containment/detonate
logic can take a `run_remote` callable and be tested without a real network.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class RemoteResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class RemoteUnreachable(RuntimeError):
    pass


def run_remote(host: str | None, user: str | None, command: str, timeout: int = 20) -> RemoteResult:
    if not host or not user:
        raise RemoteUnreachable("no SSH host/user configured")

    full_cmd = [
        "ssh",
        "-o", "ConnectTimeout=5",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        f"{user}@{host}",
        command,
    ]
    try:
        proc = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise RemoteUnreachable("`ssh` not found on this host") from exc
    except subprocess.TimeoutExpired as exc:
        raise RemoteUnreachable(f"SSH to {user}@{host} timed out") from exc

    return RemoteResult(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
