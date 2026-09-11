# Architecture

Vanta is a three-VM, network-isolated detection-engineering lab. One VM attacks,
one gets attacked and revert-and-repeats, and one stays stable and collects
evidence. The repo that ties it all together lives on the Windows host, outside
every VM.

## Why three VMs, not one or two

The machine collecting evidence must not be the machine getting compromised, and
the machine doing the attacking shouldn't be trusted with defensive telemetry
either. Three separate roles, three separate VMs:

- **siem-vm** — pure defense. Runs Wazuh and the INetSim sinkhole, and nothing
  else. It never runs attack tooling, so nothing it observes or reports is
  contaminated by having also been the attacker.
- **victim-vm** — the disposable target. Snapshotted clean before every run, so
  no matter how badly a technique, exploit, or real malware sample behaves, undoing
  it is a snapshot revert, nothing more.
- **kali-vm** — the attacker. Runs Metasploit, Nmap, and other offensive tooling,
  and is the only box in the lab that ever initiates an attack against victim-vm.
  Keeping attack tooling off both siem-vm and victim-vm means neither the
  evidence-collection box nor the target itself needs anything offensive
  installed on it.

If attacker and defender telemetry lived on the same box, a bad detonation could
take out the SIEM, the detection rules, and the whole history of the lab along
with it. If the attacker and the target were the same box — which is what a
purely locally-run Atomic Red Team setup looks like — there's no way to exercise
techniques that genuinely originate from a separate host: network scanning,
remote exploitation, C2 beaconing, lateral movement. Splitting all three apart
buys both properties at once.

## Why the repo lives on the host + GitHub

None of the three VMs is where the durable record of this project lives.
`victim-vm` gets reverted constantly by design — anything stored only there is
expected to vanish. `kali-vm` is also expected to be rebuilt or re-snapshotted
as tooling changes. `siem-vm` is the most stable of the three but is still a VM
you might rebuild, resize, or reprovision as Wazuh versions change. The Windows
host (running Claude Code) and the GitHub remote are the only two places
guaranteed to survive every VM operation. All three VMs `git clone` the repo and
pull updates; none of them is treated as a source of truth for code, docs, or
detection rules.

## Network: VMnet10 (isolated host-only), plus one narrow exception

All three VMs sit on a single VMware host-only network, **VMnet10**, with **NAT
disabled**. That means:

- No route from siem-vm or victim-vm to the real internet, ever.
- No route from any VM to your home/office LAN.
- victim-vm's only network path is VMnet10 — it can reach siem-vm and kali-vm,
  and nothing else.

The one deliberate exception: **kali-vm has a second network adapter, NAT'd to
the real internet, used only to pull attacker tooling and OS updates.** This is
necessary in practice — attack tooling changes constantly and re-downloading it
via sneakernet every time isn't sustainable — but it introduces a real risk: if
kali-vm ever routed traffic between its two interfaces, it would turn into a
bridge from the isolated VMnet10 segment straight out to the real internet,
silencing the whole point of the isolation.

That risk is closed by policy, not hope: **IP forwarding is disabled on
kali-vm** (`net.ipv4.ip_forward = 0`, verified, not assumed), and no NAT/masquerade
rule is ever added on kali-vm's isolated interface. kali-vm can *originate*
traffic on VMnet10 (it's the attacker) and can *originate* traffic on its NAT
interface (to fetch updates), but it never forwards one to the other. This is
checked as part of containment verification (see
`CONTAINMENT-AND-SAFETY.md`) — not just set once and trusted.

Your Windows host can still reach all three VMs directly (host-only networks are
reachable from the host by default), so you can browse the Wazuh dashboard from
your normal browser without going through kali-vm at all.

## siem-vm — Ubuntu Server (stable, home base, pure defense)

Runs:

- **Docker + Docker Compose**, hosting:
  - **Wazuh** (indexer, manager, dashboard) — collects and indexes agent
    telemetry, evaluates decoder/rule matches, surfaces alerts.
  - **INetSim** — a fake-internet sinkhole. Answers DNS and HTTP/HTTPS for any
    request with canned responses, and logs everything. This is what lets you
    detonate samples that expect to reach a live internet without ever letting
    them actually do so.
- All accumulated **logs, detection rules, and history** for the project.

siem-vm has no offensive tooling on it at all, and no second network adapter — it
never needs to reach the real internet.

## victim-vm — Ubuntu Desktop (disposable, snapshot every run)

Runs:

- **Wazuh agent**, shipping logs to siem-vm.
- **auditd** + **Sysmon-for-Linux**, for rich process/file/network telemetry.
- **Invoke-AtomicRedTeam** (via PowerShell/pwsh) and the atomics library, for
  running individual ATT&CK technique tests by ID, locally.
- A locked-down **detonation area** for running real malware samples once
  containment is verified.

victim-vm's only network path is VMnet10 (reaching siem-vm and kali-vm) — no
other route exists, and it has no second adapter. You snapshot it clean before
every run and revert after, whether the run was a scripted atomic, a hands-on
attack from kali-vm, or a real sample.

## kali-vm — Kali Linux (attacker, the only offense-capable box)

Runs:

- Standard Kali tooling (Metasploit, Nmap, exploitation frameworks, optionally a
  C2 framework) for attacks against victim-vm that a locally-run atomic can't
  represent: network scanning/discovery, remote exploitation, C2 beaconing,
  lateral movement.
- **Two network adapters**: one on VMnet10 (to reach victim-vm and siem-vm), one
  NAT'd to the real internet (tool/OS updates only). IP forwarding is disabled
  between them — see the network section above.

kali-vm is treated like victim-vm in one respect: it's rebuilt/re-snapshotted
periodically rather than treated as permanent state, since attack tooling and
its footprint on the box change over time.

## Data flow

```
kali-vm                    victim-vm                              siem-vm
  attacks ───VMnet10───►      execve/file/net events ──auditd──┐
                               Sysmon events           ─────────┼──►  Wazuh agent  ──►  Wazuh manager/indexer
                               atomic / sample runs     ─────────┘                          │
                                                                                              ▼
                               DNS + HTTP(S) "internet" traffic  ───────────────────────►  INetSim (sinkhole)
                                                                                              │
                                                                                       logged, never forwarded

kali-vm's NAT adapter ──► real internet   (tool updates only; never bridged to VMnet10)
```

Everything victim-vm produces — telemetry, attempted egress, and whatever
kali-vm threw at it — ends up observable on siem-vm. Nothing on VMnet10 leaves
it, except deliberately, from kali-vm's second adapter, for tooling updates
only.

## Where the daily loop fits

The `purplelab` CLI (see `tooling/`) runs on the host and orchestrates the loop:
pick a technique → run it against victim-vm (locally via Invoke-AtomicRedTeam, or
staged as an attack from kali-vm) → query Wazuh on siem-vm for what fired →
write/fix a Sigma rule in `detections/` → deploy it → confirm detection → log the
result in `journal/`. The host is the control point; kali-vm and victim-vm are
where activity happens, siem-vm is where it's observed.
