"""Configuration loading: non-secret settings from config.yaml, secrets from
a gitignored .env / real environment variables. Env vars always win.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

TOOLING_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TOOLING_DIR.parent
DEFAULT_CONFIG_PATH = TOOLING_DIR / "config.yaml"


@dataclass
class Config:
    repo_root: Path
    siem_vm_ip: str
    wazuh_base_url: str  # indexer API (alerts/archives), port 9200
    wazuh_api_base_url: str  # manager API (agent status), port 55000
    wazuh_user: str
    wazuh_password: str
    wazuh_verify_tls: bool
    victim_agent_name: str
    victim_ssh_host: str | None
    victim_ssh_user: str | None
    kali_ssh_host: str | None
    kali_ssh_user: str | None
    siem_ssh_user: str | None  # host is siem_vm_ip
    victim_vmx_path: str | None
    external_probe_ip: str
    external_probe_domain: str


def load_config(config_path: Path | None = None) -> Config:
    load_dotenv(TOOLING_DIR / ".env")

    path = config_path or Path(os.environ.get("PURPLELAB_CONFIG", DEFAULT_CONFIG_PATH))
    raw: dict = {}
    if path.exists():
        raw = yaml.safe_load(path.read_text()) or {}

    siem_vm_ip = os.environ.get("SIEM_VM_IP", raw.get("siem_vm_ip", ""))
    wazuh_base_url = os.environ.get(
        "WAZUH_BASE_URL", raw.get("wazuh_base_url") or (f"https://{siem_vm_ip}:9200" if siem_vm_ip else "")
    )
    wazuh_api_base_url = os.environ.get(
        "WAZUH_API_BASE_URL", raw.get("wazuh_api_base_url") or (f"https://{siem_vm_ip}:55000" if siem_vm_ip else "")
    )

    return Config(
        repo_root=REPO_ROOT,
        siem_vm_ip=siem_vm_ip,
        wazuh_base_url=wazuh_base_url,
        wazuh_api_base_url=wazuh_api_base_url,
        wazuh_user=os.environ.get("WAZUH_USER", ""),
        wazuh_password=os.environ.get("WAZUH_PASSWORD", ""),
        wazuh_verify_tls=str(os.environ.get("WAZUH_VERIFY_TLS", raw.get("wazuh_verify_tls", False))).lower()
        in ("1", "true", "yes"),
        victim_agent_name=os.environ.get("VICTIM_AGENT_NAME", raw.get("victim_agent_name", "victim-vm")),
        victim_ssh_host=os.environ.get("VICTIM_SSH_HOST", raw.get("victim_ssh_host")),
        victim_ssh_user=os.environ.get("VICTIM_SSH_USER", raw.get("victim_ssh_user")),
        kali_ssh_host=os.environ.get("KALI_SSH_HOST", raw.get("kali_ssh_host")),
        kali_ssh_user=os.environ.get("KALI_SSH_USER", raw.get("kali_ssh_user")),
        siem_ssh_user=os.environ.get("SIEM_SSH_USER", raw.get("siem_ssh_user")),
        victim_vmx_path=os.environ.get("VICTIM_VMX_PATH", raw.get("victim_vmx_path")),
        external_probe_ip=os.environ.get("EXTERNAL_PROBE_IP", raw.get("external_probe_ip", "1.1.1.1")),
        external_probe_domain=os.environ.get(
            "EXTERNAL_PROBE_DOMAIN", raw.get("external_probe_domain", "example.com")
        ),
    )
