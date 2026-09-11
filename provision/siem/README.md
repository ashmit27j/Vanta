# provision/siem

Provisioning for **siem-vm** (Ubuntu Server): Docker, Wazuh (indexer + manager +
dashboard), and INetSim (fake-internet sinkhole for detonation containment).

**Status:** stub. Filled in by:

- **Prompt 2** — `install.sh` (Docker + Wazuh via `docker-compose.yml`), plus a
  `Makefile` with `siem-up` / `siem-down` / `siem-logs` / `siem-status` targets.
- **Prompt 3** — INetSim service added to the compose stack (or a dedicated
  compose file here), and the DNS/routing setup so victim-vm's traffic hits the
  sinkhole.

Run this inside `siem-vm`, after cloning the repo there (see
`docs/VM-BUILD-RUNBOOK.md`), not on the Windows host.
