"""Sigma detection pipeline: parse/validate rules under detections/, convert
them to Lucene queries via pySigma, and deploy those queries as OpenSearch
Alerting monitors on siem-vm's Wazuh indexer (the indexer is an OpenSearch
fork and ships the Alerting plugin -- this is what actually runs our custom
detections, since Wazuh's own XML rule engine isn't what Sigma targets here).

Two things worth knowing before touching this file:

1. **Field mapping is a best-effort placeholder.** Sysmon-for-Linux
   (installed on victim-vm in Prompt 4) emits Windows-Sysmon-compatible
   events, and Wazuh's existing Sysmon ruleset decodes them into the same
   `data.win.eventdata.*` namespace used for Windows Sysmon. FIELD_MAPPING
   below assumes that. **Verify it against a real decoded event in the Wazuh
   dashboard once Prompts 2 and 4 are actually run** -- if the real field
   names differ, fix FIELD_MAPPING, not each rule.

2. **This targets `wazuh-archives-*`, which requires archives enabled** on
   the Wazuh manager (`logall_json: yes` in ossec.conf) -- otherwise the
   indexer only holds events Wazuh's own rules already alerted on, and a
   *new* Sigma detection would have nothing to query. Prompt 2's
   provision/siem/install.sh must enable this.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests
from sigma.backends.elasticsearch import LuceneBackend
from sigma.collection import SigmaCollection
from sigma.processing.pipeline import ProcessingItem, ProcessingPipeline
from sigma.processing.transformations import FieldMappingTransformation

from .config import Config

ARCHIVE_INDEX_PATTERN = "wazuh-archives-*"
MONITOR_SCHEDULE_MINUTES = 5

# See module docstring point 1 -- verify against real events before trusting this.
FIELD_MAPPING = {
    "Image": "data.win.eventdata.image",
    "CommandLine": "data.win.eventdata.commandLine",
    "ParentImage": "data.win.eventdata.parentImage",
    "User": "data.win.eventdata.user",
}


class SigmaPipelineError(RuntimeError):
    pass


def _pipeline() -> ProcessingPipeline:
    return ProcessingPipeline(
        items=[ProcessingItem(identifier="wazuh-sysmon-linux-fieldmap", transformation=FieldMappingTransformation(FIELD_MAPPING))]
    )


def _backend() -> LuceneBackend:
    return LuceneBackend(processing_pipeline=_pipeline())


def technique_id_for(rule_path: Path) -> str:
    """Convention: detections/<tactic>/<technique>.yml -- filename stem is the ID."""
    return rule_path.stem


def monitor_name_for(technique_id: str) -> str:
    return f"vanta-{technique_id}"


def find_rules(detections_dir: Path) -> list[Path]:
    return sorted(detections_dir.glob("*/*.yml"))


def validate_rule(rule_path: Path) -> SigmaCollection:
    """Raises SigmaPipelineError on invalid Sigma syntax; used by CI + convert."""
    try:
        return SigmaCollection.from_yaml(rule_path.read_text())
    except Exception as exc:  # pySigma raises several distinct exception types
        raise SigmaPipelineError(f"{rule_path}: {exc}") from exc


def convert_rule(rule_path: Path) -> list[str]:
    """Sigma YAML -> Lucene query string(s) (usually one per rule)."""
    collection = validate_rule(rule_path)
    return _backend().convert(collection)


def convert_all(detections_dir: Path) -> dict[Path, list[str]]:
    return {path: convert_rule(path) for path in find_rules(detections_dir)}


def _monitor_body(technique_id: str, lucene_query: str) -> dict:
    return {
        "type": "monitor",
        "name": monitor_name_for(technique_id),
        "monitor_type": "query_level_monitor",
        "enabled": True,
        "schedule": {"period": {"interval": MONITOR_SCHEDULE_MINUTES, "unit": "MINUTES"}},
        "inputs": [
            {
                "search": {
                    "indices": [ARCHIVE_INDEX_PATTERN],
                    "query": {"query": {"query_string": {"query": lucene_query}}},
                }
            }
        ],
        "triggers": [
            {
                "name": f"{technique_id}-fired",
                "severity": "3",
                "condition": {
                    "script": {
                        "source": "return ctx.results[0].hits.total.value > 0",
                        "lang": "painless",
                    }
                },
                "actions": [],
            }
        ],
    }


def _find_existing_monitor(config: Config, name: str) -> dict | None:
    resp = requests.post(
        f"{config.wazuh_base_url}/_plugins/_alerting/monitors/_search",
        json={"query": {"term": {"monitor.name.keyword": name}}},
        auth=(config.wazuh_user, config.wazuh_password),
        verify=config.wazuh_verify_tls,
        timeout=15,
    )
    resp.raise_for_status()
    hits = resp.json().get("hits", {}).get("hits", [])
    return hits[0] if hits else None


def deploy_rule(config: Config, rule_path: Path) -> str:
    """Create or update the OpenSearch Alerting monitor for this rule.
    Returns the monitor id.
    """
    technique_id = technique_id_for(rule_path)
    queries = convert_rule(rule_path)
    if len(queries) != 1:
        raise SigmaPipelineError(
            f"{rule_path}: expected exactly one Lucene query, got {len(queries)} -- "
            "split the rule or simplify its condition."
        )
    body = _monitor_body(technique_id, queries[0])
    name = monitor_name_for(technique_id)

    existing = _find_existing_monitor(config, name)
    if existing is None:
        resp = requests.post(
            f"{config.wazuh_base_url}/_plugins/_alerting/monitors",
            json=body,
            auth=(config.wazuh_user, config.wazuh_password),
            verify=config.wazuh_verify_tls,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["_id"]

    resp = requests.put(
        f"{config.wazuh_base_url}/_plugins/_alerting/monitors/{existing['_id']}"
        f"?if_seq_no={existing['_seq_no']}&if_primary_term={existing['_primary_term']}",
        json=body,
        auth=(config.wazuh_user, config.wazuh_password),
        verify=config.wazuh_verify_tls,
        timeout=15,
    )
    resp.raise_for_status()
    return existing["_id"]


@dataclass
class Finding:
    timestamp: str
    monitor_id: str


def search_findings(config: Config, monitor_id: str, since: datetime, until: datetime) -> list[Finding]:
    """Findings recorded by a monitor's trigger firing, in [since, until].

    NOTE: unverified against live infra -- the OpenSearch Alerting Findings
    API's exact response shape should be double-checked against the real
    Wazuh indexer once it exists (Prompt 2), and this adjusted if it differs.
    """
    resp = requests.post(
        f"{config.wazuh_base_url}/_plugins/_alerting/findings/_search",
        json={
            "size": 50,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"monitor_id": monitor_id}},
                        {"range": {"timestamp": {"gte": since.isoformat(), "lte": until.isoformat()}}},
                    ]
                }
            },
        },
        auth=(config.wazuh_user, config.wazuh_password),
        verify=config.wazuh_verify_tls,
        timeout=15,
    )
    resp.raise_for_status()
    hits = resp.json().get("hits", {}).get("hits", [])
    return [Finding(timestamp=h["_source"]["timestamp"], monitor_id=monitor_id) for h in hits]
