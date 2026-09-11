# Architecture

Purple Lab is a two-VM, network-isolated detection-engineering lab. One VM gets
attacked and revert-and-repeats; the other stays stable and collects evidence.
The repo that ties it all together lives on the Windows host, outside both VMs.

## Why two VMs, not one

The machine collecting evidence must not be the machine getting compromised. If a
real malware sample trashes, encrypts, or otherwise wrecks the box it's detonated
on, that has to be a cheap, disposable event — a snapshot revert, nothing more. If
attacker and defender telemetry lived on the same box, a bad detonation could take
out the SIEM, the detection rules, and the whole history of the lab along with it.

Splitting them means:

- **victim-vm** can be reverted to a clean snapshot before every single run, no
  matter how badly a technique or sample behaves.
- **siem-vm** stays up, accumulates logs and detection history across sessions,
  and is never directly exposed to whatever gets detonated.

## Why the repo lives on the host + GitHub

Neither VM is where the durable record of this project lives. `victim-vm` gets
reverted constantly by design — anything stored only there is expected to vanish.
`siem-vm` is more stable but is still a VM you might rebuild, resize, or nuke and
reprovision as Wazuh versions change. The Windows host (running Claude Code) and
the GitHub remote are the only two places guaranteed to survive every VM
operation. Both VMs `git clone` the repo and pull updates; neither is treated as
a source of truth for code, docs, or detection rules.

## Network: VMnet10 (isolated host-only)

Both VMs sit on a single VMware host-only network, **VMnet10**, with **NAT
disabled**. That means:

- No route from either VM to the real internet.
- No route from either VM to your home/office LAN.
- The only network path victim-vm has is to siem-vm, on VMnet10.
- Your Windows host can still reach both VMs (host-only networks are reachable
  from the host by default), so you can browse the Wazuh dashboard from your
  normal browser.

This is what makes it safe to detonate real malware samples: even if a sample
tries to phone home, DNS-exfil, or reach a C2 server, there is no physical path
out of VMnet10 for that traffic to take.

## siem-vm — Ubuntu Server (stable, home base)

Runs:

- **Docker + Docker Compose**, hosting:
  - **Wazuh** (indexer, manager, dashboard) — collects and indexes agent
    telemetry, evaluates decoder/rule matches, surfaces alerts.
  - **INetSim** — a fake-internet sinkhole. Answers DNS and HTTP/HTTPS for any
    request with canned responses, and logs everything. This is what lets you
    detonate samples that expect to reach a live internet without ever letting
    them actually do so.
- All accumulated **logs, detection rules, and history** for the project.

siem-vm is the box you don't casually snapshot-revert — it's meant to persist
across many detonation cycles on victim-vm.

## victim-vm — Ubuntu (disposable, snapshot every run)

Runs:

- **Wazuh agent**, shipping logs to siem-vm.
- **auditd** + **Sysmon-for-Linux**, for rich process/file/network telemetry.
- **Invoke-AtomicRedTeam** (via PowerShell/pwsh) and the atomics library, for
  running individual ATT&CK technique tests by ID.
- A locked-down **detonation area** (`/samples`-equivalent inside the VM) for
  running real malware samples once containment is verified.

victim-vm's **only** network path is to siem-vm over VMnet10 — no other route
exists. You snapshot it clean before every run and revert after, whether the run
was a scripted atomic or a real sample.

## Data flow

```
victim-vm                              siem-vm
  execve/file/net events  ──auditd──┐
  Sysmon events            ─────────┼──►  Wazuh agent  ──►  Wazuh manager/indexer
  atomic / sample runs     ─────────┘                          │
                                                                 ▼
  DNS + HTTP(S) "internet" traffic  ───────────────────────►  INetSim (sinkhole)
                                                                 │
                                                          logged, never forwarded
```

Everything victim-vm produces — telemetry and attempted egress alike — ends up
observable on siem-vm. Nothing victim-vm sends leaves VMnet10.

## Where the daily loop fits

The `purplelab` CLI (see `tooling/`) runs on the host and orchestrates the loop:
pick a technique → run it on victim-vm → query Wazuh on siem-vm for what fired →
write/fix a Sigma rule in `detections/` → deploy it → confirm detection → log the
result in `journal/`. The host is the control point; the VMs are where telemetry
is generated and collected, respectively.
