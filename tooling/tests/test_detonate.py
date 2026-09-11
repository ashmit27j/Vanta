import json
from pathlib import Path

import pytest

from purplelab import containment, detonate, ssh, wazuh
from purplelab.config import Config


def make_config(tmp_path, **overrides) -> Config:
    base = dict(
        repo_root=tmp_path,
        siem_vm_ip="192.168.110.10",
        wazuh_base_url="https://192.168.110.10:9200",
        wazuh_api_base_url="https://192.168.110.10:55000",
        wazuh_user="admin",
        wazuh_password="secret",
        wazuh_verify_tls=False,
        victim_agent_name="victim-vm",
        victim_ssh_host="192.168.110.20",
        victim_ssh_user="ubuntu",
        kali_ssh_host="192.168.110.30",
        kali_ssh_user="kali",
        siem_ssh_user="ubuntu",
        victim_vmx_path=r"C:\VMs\victim-vm\victim-vm.vmx",
        external_probe_ip="1.1.1.1",
        external_probe_domain="example.com",
    )
    base.update(overrides)
    return Config(**base)


class FakeVmrun:
    class VmrunError(RuntimeError):
        pass

    def __init__(self):
        self.reverted = None
        self.started = None

    def revert_to_snapshot(self, vmx, name):
        self.reverted = (vmx, name)

    def start(self, vmx):
        self.started = vmx


def all_good_run_remote(host, user, command, timeout=20):
    if "echo ready" in command:
        return ssh.RemoteResult(0, "ready\n", "")
    if "ping" in command:
        return ssh.RemoteResult(1, "", "100% packet loss")
    if "getent" in command:
        return ssh.RemoteResult(0, "192.168.110.10\n", "")
    if "sysctl" in command:
        return ssh.RemoteResult(0, "0\n0\n0\n", "")
    if "sha256sum" in command:
        return ssh.RemoteResult(0, "deadbeef" * 8 + "  sample.bin\n", "")
    if "ausearch" in command:
        return ssh.RemoteResult(0, "type=EXECVE ...\n", "")
    if "journalctl" in command:
        return ssh.RemoteResult(0, "{}\n", "")
    if "inetsim" in command:
        return ssh.RemoteResult(0, "log line\n", "")
    return ssh.RemoteResult(0, "", "")


def test_revert_clean_aborts_without_vmx_path(tmp_path):
    config = make_config(tmp_path, victim_vmx_path=None)
    with pytest.raises(detonate.DetonationAborted):
        detonate._revert_clean(config, FakeVmrun())


def test_revert_clean_calls_vmrun_with_clean_baseline(tmp_path):
    config = make_config(tmp_path)
    fake = FakeVmrun()
    detonate._revert_clean(config, fake)
    assert fake.reverted == (config.victim_vmx_path, detonate.CLEAN_SNAPSHOT_NAME)
    assert fake.started == config.victim_vmx_path


def test_wait_for_ssh_gives_up_after_retries(tmp_path):
    config = make_config(tmp_path)
    calls = []

    def always_fails(host, user, command, timeout=20):
        raise ssh.RemoteUnreachable("down")

    sleeps = []
    with pytest.raises(detonate.DetonationAborted):
        detonate._wait_for_ssh(config, always_fails, sleeps.append)
    assert len(sleeps) == detonate.SSH_WAIT_RETRIES


def test_run_detonation_aborts_when_containment_fails(tmp_path, monkeypatch):
    config = make_config(tmp_path)

    def egress_open_run_remote(host, user, command, timeout=20):
        if "echo ready" in command:
            return ssh.RemoteResult(0, "ready\n", "")
        if "ping" in command:
            return ssh.RemoteResult(0, "1 received", "")  # egress works -- containment FAILS
        return all_good_run_remote(host, user, command, timeout)

    monkeypatch.setattr(wazuh, "get_agent_status", lambda c, n: "active")

    with pytest.raises(detonate.DetonationAborted):
        detonate.run_detonation(
            config,
            sample_path="/home/ubuntu/samples/sample.bin",
            run_remote=egress_open_run_remote,
            vmrun_mod=FakeVmrun(),
            sleep_fn=lambda s: None,
        )

    assert not (tmp_path / "journal" / "evidence").exists()


def test_run_detonation_happy_path_bundles_evidence(tmp_path, monkeypatch):
    config = make_config(tmp_path)
    monkeypatch.setattr(wazuh, "get_agent_status", lambda c, n: "active")
    monkeypatch.setattr(wazuh, "search_alerts", lambda c, agent, since, until=None: [])

    result = detonate.run_detonation(
        config,
        sample_path="/home/ubuntu/samples/sample.bin",
        run_remote=all_good_run_remote,
        vmrun_mod=FakeVmrun(),
        sleep_fn=lambda s: None,
    )

    assert result.sample_sha256 == "deadbeef" * 8
    evidence_dir = Path(result.evidence_dir)
    assert evidence_dir.exists()
    assert (evidence_dir / "manifest.json").exists()
    assert (evidence_dir / "audit.log").exists()
    assert (evidence_dir / "sysmon.log").exists()
    assert (evidence_dir / "inetsim.log").exists()
    assert (evidence_dir / "wazuh_alerts.json").exists()

    manifest = json.loads((evidence_dir / "manifest.json").read_text())
    assert manifest["sample_sha256"] == "deadbeef" * 8
    assert all(c["passed"] for c in manifest["containment_checks"])
