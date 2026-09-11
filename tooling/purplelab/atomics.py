"""The technique catalog `purplelab pick` chooses from.

Backed by data/techniques.json -- a hand-curated subset, not the full ATT&CK
matrix. TODO: once victim-vm/kali-vm exist, prefer cross-referencing the real
Invoke-AtomicRedTeam atomics-index.yaml over this static list.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data" / "techniques.json"


@dataclass(frozen=True)
class Technique:
    id: str
    name: str
    tactic: str
    remote: bool


def load_techniques() -> list[Technique]:
    raw = json.loads(DATA_PATH.read_text())
    return [
        Technique(id=t["id"], name=t["name"], tactic=t["tactic"], remote=t["remote"])
        for t in raw["techniques"]
    ]


def get_technique(technique_id: str) -> Technique | None:
    for t in load_techniques():
        if t.id == technique_id:
            return t
    return None


def pick_uncovered(covered_ids: set[str], tactic: str | None = None) -> Technique | None:
    """First technique not yet in `covered_ids`, optionally restricted to one tactic."""
    for t in load_techniques():
        if tactic and t.tactic != tactic:
            continue
        if t.id not in covered_ids:
            return t
    return None
