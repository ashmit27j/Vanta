# provision/victim

Provisioning for **victim-vm** (Ubuntu Desktop): Wazuh agent enrollment,
auditd with a strong ruleset, Sysmon-for-Linux, PowerShell +
Invoke-AtomicRedTeam, and a locked-down `/samples` working directory.

Run this inside `victim-vm`, after cloning the repo there (see
`docs/VM-BUILD-RUNBOOK.md`):

```
make victim-provision SIEM_MANAGER_IP=192.168.110.10   # siem-vm's IP on VMnet10
make victim-verify
```

**Provision before isolating.** `install.sh` needs real package-repo access
(Wazuh's, Microsoft's, GitHub raw) to run. Do this step while victim-vm can
still reach the internet for setup, *then* lock its network adapter down to
VMnet10-only per `docs/VM-BUILD-RUNBOOK.md` before ever running an atomic or
opening a sample — never provision and detonate in the same network state.

## What gets installed

- **Wazuh agent** — via Wazuh's apt repo, pointed at `SIEM_MANAGER_IP`. Shows
  up in the Wazuh dashboard (siem-vm) within seconds of starting.
- **auditd** — ruleset in `audit.rules`, hand-assembled against this lab's
  technique catalog (`tooling/purplelab/data/techniques.json`), not adopted
  wholesale from a generic hardening baseline. See the file's own comments;
  `auditctl -l` cannot glob paths, so a few watches may need adjusting to
  match real paths once this is live.
- **Sysmon-for-Linux** — config in `sysmon-config.xml`, a deliberate
  "log everything" baseline (tune down once you've seen real volume). See
  the file's own caveat: exact supported event types and schema version
  should be checked against `sysmon -c` output once installed — this config
  is what `tooling/purplelab/sigma_pipeline.py`'s field mapping assumes.
- **PowerShell (`pwsh`) + Invoke-AtomicRedTeam** — installed via the
  project's own official one-liner, with `-getAtomics` so the atomics
  library is local. Lets `purplelab run <T-id>` (or you, by hand) run
  `Invoke-AtomicTest <T-id>`.
- **`~/samples`** — mode 700, for real-sample detonation staging. Never the
  Windows host, never a shared folder — see
  `docs/CONTAINMENT-AND-SAFETY.md`.

`make victim-verify` checks all of the above are actually running/present
and prints a clear NOT FOUND / NOT RUNNING per item rather than failing
silently.

**After this:** snapshot victim-vm as `clean-baseline` — this is the
snapshot every future run reverts to.
