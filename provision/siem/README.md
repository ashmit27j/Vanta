# provision/siem

Provisioning for **siem-vm** (Ubuntu Server): Docker + the official Wazuh
single-node stack (indexer + manager + dashboard), and INetSim (fake-internet
sinkhole for detonation containment).

Run this inside `siem-vm`, after cloning the repo there (see
`docs/VM-BUILD-RUNBOOK.md`), not on the Windows host:

```
make siem-up      # install.sh (Wazuh) + inetsim/install.sh (sinkhole)
make siem-status
make siem-logs
make siem-down
```

## Wazuh (`install.sh`)

Clones the upstream [`wazuh/wazuh-docker`](https://github.com/wazuh/wazuh-docker)
repo at a pinned tag (`WAZUH_VERSION`, default set in the script) rather than
vendoring a hand-written compose file -- that repo's cert-generation flow and
config layout change between releases, so deferring to upstream's own
maintained files is more reliable than us guessing. It also enables Wazuh
**archives** (`<logall_json>yes</logall_json>`), which the Sigma pipeline
(`detections/`, Prompt 6) needs -- without archives, the indexer only holds
events Wazuh's own built-in rules already alerted on, and a *new* detection
would have nothing to query.

**Reach the dashboard from your host browser** at `https://<siem-vm-ip>/`
over VMnet10 (the Windows host can reach host-only networks directly). Default
credentials live under the cloned `wazuh-docker/single-node/config` directory
-- change them before this box sees real use, even though it's isolated.

## INetSim (`inetsim/install.sh`)

Installs INetSim from the official source tarball (not available in default
Ubuntu repos), configures it to answer DNS/HTTP/HTTPS as siem-vm's own IP, and
runs it as a systemd service (`systemctl status/restart inetsim`,
`journalctl -u inetsim -f`). See the script's own caveat comment: the exact
Perl dependency list is best-effort -- if `inetsim --check` reports missing
modules, `apt install` them and re-run (idempotent).

After this, point victim-vm's DNS and default route at siem-vm's IP (see
`docs/VM-BUILD-RUNBOOK.md` and `provision/victim/`), then verify from
victim-vm with `purplelab containment-check` (see `tooling/`).
