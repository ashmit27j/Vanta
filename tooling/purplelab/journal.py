"""Reads and writes the daily-loop history: journal/entries.jsonl (machine
-readable, one JSON object per line) and journal/LOG.md (human-readable).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ENTRIES_FILENAME = "entries.jsonl"
LOG_FILENAME = "LOG.md"


@dataclass
class Entry:
    technique_id: str
    tactic: str
    date: str  # YYYY-MM-DD
    timestamp: str  # ISO 8601, UTC
    caught_blind: bool
    sigma_rule: str | None
    notes: str
    time_to_detect_seconds: float | None


def _journal_dir(repo_root: Path) -> Path:
    d = repo_root / "journal"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _entries_path(repo_root: Path) -> Path:
    return _journal_dir(repo_root) / ENTRIES_FILENAME


def _log_path(repo_root: Path) -> Path:
    return _journal_dir(repo_root) / LOG_FILENAME


def read_entries(repo_root: Path) -> list[Entry]:
    path = _entries_path(repo_root)
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            entries.append(Entry(**json.loads(line)))
    return entries


def append_entry(repo_root: Path, entry: Entry) -> None:
    path = _entries_path(repo_root)
    with path.open("a") as f:
        f.write(json.dumps(asdict(entry)) + "\n")

    caught = "caught it" if not entry.caught_blind else "MISSED (caught blind)"
    ttd = f"{entry.time_to_detect_seconds:.1f}s" if entry.time_to_detect_seconds is not None else "n/a"
    section = (
        f"\n## {entry.date} -- {entry.technique_id} ({entry.tactic})\n\n"
        f"- Result: {caught}\n"
        f"- Time to detect: {ttd}\n"
        f"- Sigma rule: {entry.sigma_rule or '(none yet)'}\n"
        f"- Notes: {entry.notes or '(none)'}\n"
    )
    with _log_path(repo_root).open("a") as f:
        f.write(section)


def covered_technique_ids(repo_root: Path) -> set[str]:
    return {e.technique_id for e in read_entries(repo_root)}


def current_streak_days(repo_root: Path) -> int:
    """Consecutive days (ending today or yesterday) with at least one entry.

    Streaks are measured in the user's local calendar day, matching how
    `Entry.date` is stamped by the CLI (see commands.cmd_log) -- using UTC
    here would silently break the streak for anyone west of UTC at night.
    """
    entry_dates = {date.fromisoformat(e.date) for e in read_entries(repo_root)}
    if not entry_dates:
        return 0

    today = date.today()
    cursor = today if today in entry_dates else today - timedelta(days=1)
    if cursor not in entry_dates:
        return 0

    streak = 0
    while cursor in entry_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def recent_entries(repo_root: Path, limit: int = 5) -> list[Entry]:
    return read_entries(repo_root)[-limit:][::-1]
