# provision/victim

Provisioning for **victim-vm** (Ubuntu Desktop): Wazuh agent enrollment, auditd
with a strong ruleset, Sysmon-for-Linux, PowerShell + Invoke-AtomicRedTeam, and a
locked-down `/samples` working directory for detonation.

**Status:** stub. Filled in by **Prompt 4** — `install.sh`, `audit.rules`,
`sysmon-config.xml`, and a `Makefile` with `victim-provision` / `victim-verify`
targets.

Run this inside `victim-vm`, after cloning the repo there (see
`docs/VM-BUILD-RUNBOOK.md`), not on the Windows host. Before running, confirm
`victim-vm` cannot reach the real internet (see
`docs/CONTAINMENT-AND-SAFETY.md`).
