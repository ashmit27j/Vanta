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

## The daily loop

1. `purplelab today` — see your streak and what's next.
2. Revert victim-vm to its clean baseline snapshot.
3. `purplelab pick` → `purplelab run <T-id>` — run an ATT&CK technique against
   victim-vm (a local atomic, or a hands-on attack staged from kali-vm).
4. `purplelab check <T-id>` — query Wazuh: did anything fire? time-to-detect?
5. Write or fix a Sigma rule in `detections/`, deploy it, re-run, confirm it fires.
6. `purplelab log <T-id>` — record the result, commit, push.

Fifteen minutes. Every entry is one ATT&CK technique understood from both sides.

## Repo layout

| Path | Purpose |
|---|---|
| `docs/` | Architecture, VM build runbook, safety rules, the full build prompt chain |
| `provision/siem/` | Stand up Wazuh + INetSim on siem-vm |
| `provision/victim/` | Enroll the Wazuh agent, auditd, Sysmon, Atomic Red Team on victim-vm |
| `tooling/` | The `purplelab` Python CLI — the daily loop, containment checks, Sigma pipeline, coverage |
| `detections/` | Sigma rules, one file per ATT&CK technique |
| `journal/` | Daily-loop history: what ran, what fired, time-to-detect |
| `samples/` | Real malware samples for detonation — gitignored, never committed |

## Status

Early build-out, following the prompt chain in
[`docs/prompt-chain.md`](docs/prompt-chain.md). The lab isn't operational yet —
docs and scaffolding exist; VM provisioning and the CLI are in progress.

## Safety

**This is a contained lab. Never run techniques or samples against systems you
don't own.** The isolation described above (host-only network, no NAT, no
bridging) is what makes real-malware detonation safe here — see
[`docs/CONTAINMENT-AND-SAFETY.md`](docs/CONTAINMENT-AND-SAFETY.md) before working
with anything beyond scripted Atomic Red Team tests.

## License

MIT — see [`LICENSE`](LICENSE).
