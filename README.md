# Vanta

[![CI](https://github.com/ashmit27j/Vanta/actions/workflows/ci.yml/badge.svg)](https://github.com/ashmit27j/Vanta/actions/workflows/ci.yml)

**Vanta** is a contained, three-VM purple-team home lab: attack, defend, and
detect, on hardware you own, fully isolated from the real internet.

Every day, the loop is the same: launch one ATT&CK technique — a scripted Atomic
Red Team test, or a hands-on attack from a dedicated Kali box — against an Ubuntu
target, check whether Wazuh caught it, write or fix a Sigma detection until it
does, and log the result. Real malware samples are in scope too, once containment
is verified, because the network gives them nowhere to go.

## Why "Vanta"

A vanta is the black backing behind a two-way mirror: the layer that lets you
watch without being seen. That's the SIEM side of this lab — defense that
observes everything happening on the target without ever being part of the
attack surface itself.

## Architecture

```
WINDOWS HOST — VMware Workstation, git, this repo, Claude Code runs here
   │
   └─ VMnet10  (host-only, ISOLATED: no NAT, no route to internet or your LAN)
        │
        ├─ siem-vm    (Ubuntu Server)   STABLE, pure defense — never attacks
        │    • Docker + Wazuh (indexer / manager / dashboard)
        │    • INetSim container = fake internet (DNS + HTTP sinkhole)
        │    • holds all logs, detection rules, and history
        │
        ├─ victim-vm  (Ubuntu Desktop)  DISPOSABLE — snapshot before every run
        │    • Wazuh agent → ships telemetry to siem-vm
        │    • auditd + Sysmon-for-Linux
        │    • Invoke-AtomicRedTeam, for locally-run ATT&CK technique tests
        │    • its ONLY network path is VMnet10 (siem-vm + kali-vm)
        │
        └─ kali-vm    (Kali Linux)      ATTACKER — remote-style attacks
             • Metasploit / Nmap / C2 tooling, for exploitation, recon,
               lateral movement — attacks victim-vm that a locally-run
               atomic can't represent
             • second adapter (NAT) for tool updates only — no IP forwarding,
               so it can never bridge VMnet10 to the real internet
```

Three roles, three VMs, deliberately kept apart:

- **siem-vm** never runs attack tooling. If it isn't trustworthy, nothing it
  reports is trustworthy either.
- **victim-vm** is disposable by design — reverted to a clean snapshot before
  every technique or sample, so a bad run costs nothing but a few seconds.
- **kali-vm** is the only box that reaches attack tooling, and the only one with
  any path (a deliberately narrow one) to the real internet — for pulling tool
  updates, never for routing victim-vm's traffic anywhere.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design rationale
and [`docs/VM-BUILD-RUNBOOK.md`](docs/VM-BUILD-RUNBOOK.md) for exact VMware
Workstation build steps, and
[`docs/CONTAINMENT-AND-SAFETY.md`](docs/CONTAINMENT-AND-SAFETY.md) for the rules
that keep it safe to detonate real samples.

## Quickstart

1. Clone this repo on your Windows host (VMware Workstation, 32GB+ RAM
   recommended) and install the CLI:
   ```
   pip install -e tooling/[dev]
   ```
2. Build the lab: follow [`docs/VM-BUILD-RUNBOOK.md`](docs/VM-BUILD-RUNBOOK.md)
   to stand up the isolated `VMnet10` network and all three VMs, then work
   through the rest of [`docs/prompt-chain.md`](docs/prompt-chain.md) to
   provision Wazuh, the sinkhole, and the attack/target tooling.
3. Fill in `tooling/config.yaml` (VM IPs, SSH users) and `tooling/.env`
   (Wazuh credentials — copy from `tooling/.env.example`, never commit it).
4. Run `purplelab today` and start the daily loop below.

## The daily loop

1. `purplelab today` — see your streak and what's next.
2. Revert victim-vm to its clean baseline snapshot.
3. `purplelab pick` → `purplelab run <T-id>` — run an ATT&CK technique against
   victim-vm (a local atomic, or a hands-on attack staged from kali-vm).
4. `purplelab check <T-id>` — query Wazuh: did anything fire? time-to-detect?
5. Write or fix a Sigma rule in `detections/`, deploy it, re-run, confirm it fires.
6. `purplelab log <T-id>` — record the result, commit, push.

Fifteen minutes. Every entry is one ATT&CK technique understood from both sides.

## Coverage report

`purplelab coverage` (or `make coverage`) generates
`coverage/navigator-layer.json` — load it at the
[ATT&CK Navigator](https://mitre-attack.github.io/attack-navigator/) via
*Open Existing Layer → Upload from local* to see technique coverage on the
real matrix — and `coverage/report.html`, a self-contained, light/dark-aware
dashboard: coverage % by tactic, streak, a time-to-detect trend, and what's
left to cover.

_(Screenshot placeholder — once the lab has real data, replace this with a
screenshot of `coverage/report.html`.)_

## Repo layout

| Path | Purpose |
|---|---|
| `docs/` | Architecture, VM build runbook, safety rules, the full build prompt chain |
| `provision/siem/` | Stand up Wazuh + INetSim on siem-vm |
| `provision/victim/` | Enroll the Wazuh agent, auditd, Sysmon, Atomic Red Team on victim-vm |
| `provision/kali/` | Verify/update attack tooling and network isolation on kali-vm |
| `tooling/` | The `purplelab` Python CLI — the daily loop, Sigma pipeline, coverage, containment checks, detonation |
| `detections/` | Sigma rules, one file per ATT&CK technique |
| `journal/` | Daily-loop history: what ran, what fired, time-to-detect |
| `samples/` | Real malware samples for detonation — gitignored, never committed |

## Status

The `purplelab` CLI is fully built (pick/run/check/log/today, the Sigma
pipeline, coverage reports, containment-check, and the safety-gated
detonation workflow), with 43 passing tests covering everything that doesn't
need live infrastructure. Provisioning scripts for all three VMs are written
too (`provision/siem/`, `provision/victim/`, `provision/kali/`) — syntax
-checked, and each flagged with clear caveats anywhere it depends on details
(exact package/config layouts, Sysmon-for-Linux's supported event schema)
that can only be confirmed once the real box exists.

**The VMs themselves don't exist yet** — that's the next step, following
[`docs/VM-BUILD-RUNBOOK.md`](docs/VM-BUILD-RUNBOOK.md) and then actually
*running* Prompts 2, 3, 4, 4B's scripts inside each VM (see
[`docs/prompt-chain.md`](docs/prompt-chain.md)). Everything that talks to a
real VM (`run`/`check` execution, `containment-check`, `deploy`/`sigma test`,
`detonate`, and all the provisioning scripts themselves) is written and
tested against injected fakes / static analysis, but unverified against real
Wazuh/VMware/Kali until then.

## Roadmap

- **CALDERA automation** — orchestrate multi-technique campaigns instead of
  one atomic at a time.
- **Windows victim VM** — a second target alongside victim-vm, for
  Windows-native telemetry (ETW, native Sysmon) and technique coverage.
- **Morning auto-run** — pick and run a random uncovered technique each
  morning automatically, diff the resulting alerts against the prior day, and
  surface a digest instead of waiting for a manual `purplelab pick`.
- **Grow kali-vm's tooling** — a lightweight C2 framework (e.g. Sliver) for
  realistic multi-stage exercises beyond single exploits/scans.
- **Expand the technique catalog** — `tooling/purplelab/data/techniques.json`
  is a curated ~26 techniques, not the full ATT&CK matrix.

## Safety

**This is a contained lab. Never run techniques or samples against systems you
don't own.** The isolation described above (host-only network, no NAT, no
bridging) is what makes real-malware detonation safe here — see
[`docs/CONTAINMENT-AND-SAFETY.md`](docs/CONTAINMENT-AND-SAFETY.md) before working
with anything beyond scripted Atomic Red Team tests.

## License

MIT — see [`LICENSE`](LICENSE).
