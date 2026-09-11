import json
from pathlib import Path

from purplelab import coverage, journal

REAL_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _seed_fake_repo(tmp_path: Path):
    """A tmp repo with one detected technique (T1053.003, has a rule file
    copied from the real seed rule) and one exercised-but-undetected one.
    """
    detections = tmp_path / "detections" / "persistence"
    detections.mkdir(parents=True)
    real_rule = REAL_REPO_ROOT / "detections" / "persistence" / "T1053.003.yml"
    (detections / "T1053.003.yml").write_text(real_rule.read_text())

    entry = journal.Entry(
        technique_id="T1082",
        tactic="discovery",
        date="2026-09-10",
        timestamp="2026-09-10T10:00:00+00:00",
        caught_blind=True,
        sigma_rule=None,
        notes="",
        time_to_detect_seconds=None,
    )
    journal.append_entry(tmp_path, entry)


def test_detected_technique_ids(tmp_path):
    _seed_fake_repo(tmp_path)
    assert coverage.detected_technique_ids(tmp_path) == {"T1053.003"}


def test_build_navigator_layer_marks_detected_and_exercised(tmp_path):
    _seed_fake_repo(tmp_path)
    layer = coverage.build_navigator_layer(tmp_path)

    by_id = {t["techniqueID"]: t for t in layer["techniques"]}
    assert by_id["T1053.003"]["score"] == 100
    assert by_id["T1082"]["score"] == 40
    assert "T1046" not in by_id  # never touched -- not in the layer at all


def test_navigator_layer_is_valid_json_shape(tmp_path):
    _seed_fake_repo(tmp_path)
    layer = coverage.build_navigator_layer(tmp_path)
    # round-trips through json without error, has the fields Navigator requires
    reparsed = json.loads(json.dumps(layer))
    assert reparsed["domain"] == "enterprise-attack"
    assert "versions" in reparsed


def test_tactic_breakdown_counts_correctly(tmp_path):
    _seed_fake_repo(tmp_path)
    rows = coverage.tactic_breakdown(tmp_path)
    persistence = next(r for r in rows if r["tactic"] == "persistence")
    assert persistence["covered"] >= 1


def test_time_to_detect_series_skips_entries_without_ttd(tmp_path):
    _seed_fake_repo(tmp_path)  # T1082 entry has no time_to_detect_seconds
    assert coverage.time_to_detect_series(tmp_path) == []


def test_write_coverage_creates_both_files(tmp_path):
    _seed_fake_repo(tmp_path)
    layer_path, report_path = coverage.write_coverage(tmp_path)
    assert layer_path.exists()
    assert report_path.exists()
    assert "Vanta Coverage" in report_path.read_text()
    json.loads(layer_path.read_text())  # valid JSON
