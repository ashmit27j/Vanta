from datetime import date, timedelta, timezone, datetime

from purplelab import journal


def make_entry(technique_id="T1053.003", tactic="persistence", on_date=None, caught_blind=False):
    d = on_date or date.today()
    return journal.Entry(
        technique_id=technique_id,
        tactic=tactic,
        date=d.isoformat(),
        timestamp=datetime.now(timezone.utc).isoformat(),
        caught_blind=caught_blind,
        sigma_rule=None,
        notes="",
        time_to_detect_seconds=None,
    )


def test_append_and_read_entries(tmp_path):
    journal.append_entry(tmp_path, make_entry("T1053.003"))
    journal.append_entry(tmp_path, make_entry("T1059.004"))

    entries = journal.read_entries(tmp_path)
    assert [e.technique_id for e in entries] == ["T1053.003", "T1059.004"]


def test_append_entry_writes_markdown_log(tmp_path):
    journal.append_entry(tmp_path, make_entry("T1053.003"))
    log_text = (tmp_path / "journal" / "LOG.md").read_text()
    assert "T1053.003" in log_text
    assert "persistence" in log_text


def test_covered_technique_ids(tmp_path):
    journal.append_entry(tmp_path, make_entry("T1053.003"))
    journal.append_entry(tmp_path, make_entry("T1059.004"))
    assert journal.covered_technique_ids(tmp_path) == {"T1053.003", "T1059.004"}


def test_streak_zero_with_no_entries(tmp_path):
    assert journal.current_streak_days(tmp_path) == 0


def test_streak_counts_consecutive_days_ending_today(tmp_path):
    today = date.today()
    journal.append_entry(tmp_path, make_entry("T1", on_date=today))
    journal.append_entry(tmp_path, make_entry("T2", on_date=today - timedelta(days=1)))
    journal.append_entry(tmp_path, make_entry("T3", on_date=today - timedelta(days=2)))
    # gap here breaks the streak
    journal.append_entry(tmp_path, make_entry("T4", on_date=today - timedelta(days=5)))

    assert journal.current_streak_days(tmp_path) == 3


def test_streak_still_counts_if_today_has_no_entry_yet(tmp_path):
    yesterday = date.today() - timedelta(days=1)
    journal.append_entry(tmp_path, make_entry("T1", on_date=yesterday))
    assert journal.current_streak_days(tmp_path) == 1


def test_streak_breaks_if_more_than_a_day_has_passed(tmp_path):
    two_days_ago = date.today() - timedelta(days=2)
    journal.append_entry(tmp_path, make_entry("T1", on_date=two_days_ago))
    assert journal.current_streak_days(tmp_path) == 0


def test_recent_entries_returns_newest_first(tmp_path):
    for i in range(3):
        journal.append_entry(tmp_path, make_entry(f"T{i}"))
    recent = journal.recent_entries(tmp_path, limit=2)
    assert [e.technique_id for e in recent] == ["T2", "T1"]
