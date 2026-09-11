from pathlib import Path

from purplelab import containment, ssh, wazuh
from purplelab.config import Config


def make_config(**overrides) -> Config:
    base = dict(
        repo_root=Path("."),
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
        victim_vmx_path=None,
        external_probe_ip="1.1.1.1",
        external_probe_domain="example.com",
    )
    base.update(overrides)
    return Config(**base)


def make_run_remote(responses: dict[str, ssh.RemoteResult]):
    """responses: substring-of-command -> RemoteResult to return."""

    def _fake(host, user, command, timeout=20):
        for substring, result in responses.items():
            if substring in command:
                return result
        raise AssertionError(f"no fake response configured for command: {command!r}")

    return _fake


def test_no_external_egress_passes_when_ping_fails():
    run_remote = make_run_remote({"ping": ssh.RemoteResult(1, "", "100% packet loss")})
    result = containment.check_no_external_egress(make_config(), run_remote)
    assert result.passed


def test_no_external_egress_fails_when_ping_succeeds():
    run_remote = make_run_remote({"ping": ssh.RemoteResult(0, "1 packets transmitted, 1 received", "")})
    result = containment.check_no_external_egress(make_config(), run_remote)
    assert not result.passed


def test_no_external_egress_fails_closed_when_unreachable():
    def _raise(host, user, command, timeout=20):
        raise ssh.RemoteUnreachable("no route to victim-vm")

    result = containment.check_no_external_egress(make_config(), _raise)
    assert not result.passed
    assert "could not verify" in result.detail


def test_dns_via_sinkhole_passes_when_resolves_to_siem_ip():
    run_remote = make_run_remote({"getent": ssh.RemoteResult(0, "192.168.110.10\n", "")})
    result = containment.check_dns_via_sinkhole(make_config(), run_remote)
    assert result.passed


def test_dns_via_sinkhole_fails_when_resolves_elsewhere():
    run_remote = make_run_remote({"getent": ssh.RemoteResult(0, "8.8.8.8\n", "")})
    result = containment.check_dns_via_sinkhole(make_config(), run_remote)
    assert not result.passed


def test_kali_no_bridging_passes_when_forwarding_off_and_no_masquerade():
    run_remote = make_run_remote({"sysctl": ssh.RemoteResult(0, "0\n0\n0\n", "")})
    result = containment.check_kali_no_bridging(make_config(), run_remote)
    assert result.passed


def test_kali_no_bridging_fails_when_forwarding_on():
    run_remote = make_run_remote({"sysctl": ssh.RemoteResult(0, "1\n0\n0\n", "")})
    result = containment.check_kali_no_bridging(make_config(), run_remote)
    assert not result.passed


def test_kali_no_bridging_fails_when_masquerade_rules_exist():
    run_remote = make_run_remote({"sysctl": ssh.RemoteResult(0, "0\n0\n2\n", "")})
    result = containment.check_kali_no_bridging(make_config(), run_remote)
    assert not result.passed


def test_wazuh_agent_connected_uses_manager_api_status(monkeypatch):
    monkeypatch.setattr(wazuh, "get_agent_status", lambda config, name: "active")
    result = containment.check_wazuh_agent_connected(make_config())
    assert result.passed


def test_wazuh_agent_connected_fails_when_disconnected(monkeypatch):
    monkeypatch.setattr(wazuh, "get_agent_status", lambda config, name: "disconnected")
    result = containment.check_wazuh_agent_connected(make_config())
    assert not result.passed


def test_run_all_fails_closed_with_no_ssh_config_at_all(monkeypatch):
    monkeypatch.setattr(wazuh, "get_agent_status", lambda config, name: (_ for _ in ()).throw(
        wazuh.WazuhConnectionError("no Wazuh configured")
    ))
    config = make_config(victim_ssh_host=None, victim_ssh_user=None, kali_ssh_host=None, kali_ssh_user=None)
    results = containment.run_all(config)
    assert all(not r.passed for r in results)
