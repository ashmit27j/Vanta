"""Ephemeral per-technique run state: when did `purplelab run <T-id>` start,
so `purplelab check <T-id>` knows what time window to query Wazuh for.

Lives under journal/.state/ -- local session state, not meant to be committed
(see .gitignore).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class RunState:
    technique_id: str
    started_at: str  # ISO 8601, UTC
    mode: str  # "local" (Invoke-AtomicTest on victim-vm) or "remote" (staged from kali-vm)


def _state_dir(repo_root: Path) -> Path:
    d = repo_root / "journal" / ".state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _state_path(repo_root: Path, technique_id: str) -> Path:
    return _state_dir(repo_root) / f"{technique_id}.json"


def start_run(repo_root: Path, technique_id: str, mode: str) -> RunState:
    state = RunState(
        technique_id=technique_id,
        started_at=datetime.now(timezone.utc).isoformat(),
        mode=mode,
    )
    _state_path(repo_root, technique_id).write_text(json.dumps(asdict(state), indent=2))
    return state


def get_run(repo_root: Path, technique_id: str) -> RunState | None:
    path = _state_path(repo_root, technique_id)
    if not path.exists():
        return None
    return RunState(**json.loads(path.read_text()))


def clear_run(repo_root: Path, technique_id: str) -> None:
    path = _state_path(repo_root, technique_id)
    if path.exists():
        path.unlink()
