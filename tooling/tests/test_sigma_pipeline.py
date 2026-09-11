from pathlib import Path

import pytest

from purplelab import sigma_pipeline

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SEED_RULE = REPO_ROOT / "detections" / "persistence" / "T1053.003.yml"


def test_seed_rule_exists():
    assert SEED_RULE.exists()


def test_technique_id_for_uses_filename_stem():
    assert sigma_pipeline.technique_id_for(SEED_RULE) == "T1053.003"


def test_monitor_name_for():
    assert sigma_pipeline.monitor_name_for("T1053.003") == "vanta-T1053.003"


def test_validate_rule_parses_seed_rule():
    collection = sigma_pipeline.validate_rule(SEED_RULE)
    assert len(list(collection.rules)) == 1


def test_validate_rule_rejects_garbage(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text("not: a valid\nsigma rule at all: [")
    with pytest.raises(sigma_pipeline.SigmaPipelineError):
        sigma_pipeline.validate_rule(bad)


def test_convert_rule_produces_mapped_lucene_query():
    queries = sigma_pipeline.convert_rule(SEED_RULE)
    assert len(queries) == 1
    query = queries[0]
    # field mapping applied -- generic Sigma field names never leak through as query fields
    assert "data.win.eventdata.image" in query
    assert "data.win.eventdata.commandLine" in query
    assert "Image:" not in query
    assert "CommandLine:" not in query
    assert "crontab" in query


def test_find_rules_finds_seed_rule():
    rules = sigma_pipeline.find_rules(REPO_ROOT / "detections")
    assert SEED_RULE in rules
