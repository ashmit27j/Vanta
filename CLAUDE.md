# CLAUDE.md — Vanta conventions

This file documents how work in this repo should be done, so Claude Code stays
consistent across sessions and across the daily-loop lifecycle. Read this before
making changes.

## What this repo is

Vanta: a contained, three-VM purple-team home lab (siem-vm = defense, victim-vm =
target, kali-vm = attacker). `docs/prompt-chain.md` is the source of truth for the
build plan — it lists the full prompt chain and which prompts need a live VM vs.
which are pure authoring. If you're picking up mid-chain, check that file and
`journal/` / recent commits to see what's already done.

## Directory layout

| Path | Purpose |
|---|---|
| `docs/` | Architecture, VM build runbook, safety rules, the prompt chain itself |
| `provision/siem/` | Scripts + compose files to stand up Wazuh + INetSim on siem-vm |
| `provision/victim/` | Scripts to enroll the Wazuh agent, auditd, Sysmon, Atomic Red Team on victim-vm |
| `provision/kali/` | Scripts to provision attack tooling on kali-vm |
| `tooling/` | The `purplelab` Python CLI package (daily loop, containment checks, Sigma pipeline, coverage) |
| `detections/` | Sigma rules, one file per technique, organized by tactic |
| `journal/` | Daily-loop history: JSON + markdown entries, evidence bundles (gitignored) |
| `samples/` | Real malware samples for detonation — **gitignored, never committed** |

## Conventions

- **Python** is the tooling language (the `purplelab` CLI). Target Python 3.11+,
  use `pyproject.toml`, keep it installable via `pipx`. Write tests for anything
  with real logic (journal parsing, coverage scoring, Sigma conversion) — not for
  thin CLI wrappers.
- **Docker Compose** is how Wazuh and INetSim get stood up on siem-vm. Pin image
  versions explicitly; never use `:latest` in a committed compose file.
- **Bash** is used for provisioning scripts (`provision/siem/*.sh`,
  `provision/victim/*.sh`, `provision/kali/*.sh`). Every provisioning script must
  be **idempotent** — safe to re-run after a partial failure or on an
  already-provisioned box. Check before you install/enroll/configure; don't
  blindly overwrite.
- **Sigma** is the detection rule format. Rules live at
  `detections/<tactic>/<technique>.yml` (tactic = ATT&CK tactic slug, e.g.
  `persistence`, `execution`; technique = ATT&CK technique ID, e.g. `T1053.003`).
- Prefer editing/extending existing scripts and modules over duplicating logic.

## Safety rules that are non-negotiable

These come from `docs/CONTAINMENT-AND-SAFETY.md` — do not weaken them when writing
code or docs:

- victim-vm and siem-vm must have **no route to the real internet**. Any tooling
  that touches the network (containment checks, detonation workflow) must **fail
  closed**: if it can't positively confirm isolation, it treats the lab as unsafe.
- kali-vm is the *only* VM with a real-internet path (a second, NAT'd adapter,
  for tool updates only). It must never forward traffic between that adapter and
  its VMnet10 adapter — IP forwarding off, no NAT/masquerade rule bridging the
  two. Containment checks must verify this, not assume it.
- Real malware samples are **never** committed to git. `samples/` is gitignored;
  don't add exceptions to that rule.
- Secrets (Wazuh API creds, etc.) come from a gitignored `.env` / environment
  variables — never hardcode credentials or IPs-with-creds into committed files.
  Commit `*.env.example` templates instead.
- Detonation workflows must snapshot before and remind the user to revert after.
  Don't build anything that detonates without that sequence.

## Working style for this project

- Everything should be idempotent — provisioning scripts, CLI commands, Sigma
  deploy — re-running should be safe.
- Prompts that run *inside* the VMs (siem-vm, victim-vm, kali-vm provisioning and
  verification) need a human to verify results (dashboard loads, containment
  fails closed, agent connects, kali-vm forwarding is off). Never mark those
  steps done without that verification — leave a TODO instead of guessing.
- Commit after each meaningful unit of work (roughly: after each prompt in the
  chain), with a clear message. Small, portfolio-readable history matters here.
