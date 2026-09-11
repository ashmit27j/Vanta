"""Minimal Wazuh indexer client: query alerts for a given agent in a time
window. Talks to the indexer's OpenSearch-compatible REST API directly
(wazuh-alerts-* index) rather than pulling in a full SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import requests

from .config import Config


class WazuhConnectionError(RuntimeError):
    pass


@dataclass
class Alert:
    timestamp: str
    rule_id: str
    rule_description: str
    rule_level: int


def search_alerts(config: Config, agent_name: str, since: datetime, until: datetime | None = None) -> list[Alert]:
    if not config.wazuh_base_url or not config.wazuh_user:
        raise WazuhConnectionError(
            "Wazuh isn't configured -- set siem_vm_ip in tooling/config.yaml and "
            "WAZUH_USER/WAZUH_PASSWORD in tooling/.env (see .env.example)."
        )

    query = {
        "size": 200,
        "sort": [{"timestamp": "asc"}],
        "query": {
            "bool": {
                "filter": [
                    {"term": {"agent.name": agent_name}},
                    {
                        "range": {
                            "timestamp": {
                                "gte": since.isoformat(),
                                **({"lte": until.isoformat()} if until else {}),
                            }
                        }
                    },
                ]
            }
        },
    }

    try:
        resp = requests.post(
            f"{config.wazuh_base_url}/wazuh-alerts-*/_search",
            json=query,
            auth=(config.wazuh_user, config.wazuh_password),
            verify=config.wazuh_verify_tls,
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise WazuhConnectionError(f"could not reach Wazuh indexer at {config.wazuh_base_url}: {exc}") from exc

    hits = resp.json().get("hits", {}).get("hits", [])
    alerts = []
    for hit in hits:
        src = hit["_source"]
        rule = src.get("rule", {})
        alerts.append(
            Alert(
                timestamp=src.get("timestamp", ""),
                rule_id=str(rule.get("id", "")),
                rule_description=rule.get("description", ""),
                rule_level=int(rule.get("level", 0)),
            )
        )
    return alerts


def check_agent_connected(config: Config, agent_name: str) -> bool:
    """Best-effort liveness check: does the agent have at least one recent
    alert/event indexed? A real agent-status API call is added once the
    Wazuh manager is up (Prompt 2) -- this is deliberately conservative.
    """
    try:
        resp = requests.get(
            f"{config.wazuh_base_url}/_cluster/health",
            auth=(config.wazuh_user, config.wazuh_password),
            verify=config.wazuh_verify_tls,
            timeout=10,
        )
        return resp.ok
    except requests.RequestException:
        return False
