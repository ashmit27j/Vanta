# Vanta — Build Guide & Claude Code Prompt Chain

A contained, three-VM purple-team lab you attack and defend on your own machine.
You run one Atomic Red Team technique (or a hands-on attack from a dedicated
Kali box), check whether your monitoring caught it, write or fix a detection,
and confirm it fires — every day. Real malware samples are in scope, so the
network is fully isolated except for one narrow, verified exception on the
attacker box.

> **Note:** this guide originally shipped as a two-VM design (siem-vm + INetSim
> doubling as the attack source via locally-run atomics only). It was revised to
> three VMs — adding a dedicated **kali-vm** attacker box — so the lab can also
> exercise attacks that genuinely originate from a separate host: network
> scanning, remote exploitation, C2 beaconing, lateral movement. Prompts 0–3
> below predate that change and are left as originally run; **Prompt 4B** adds
> kali-vm provisioning.

---

## Your setup (confirmed)

- **Host:** Windows + VMware Workstation, **32GB RAM**
- **Victim VM:** **Ubuntu Desktop** (attacked + detonated on; snapshot every run)
- **SIEM VM:** Ubuntu Server running Wazuh **+ INetSim fake-internet on the same box**
- **Kali VM:** Kali Linux, the only attacker box, dual-homed (VMnet10 + NAT for tool updates only)
- **Tooling:** Python
- **Repo:** public GitHub, portfolio-grade from day one
- **Scope:** full containment now so real samples are safe when you're ready

### VM sizing (with 32GB host)

| VM | vCPU | RAM | Disk | Notes |
|---|---|---|---|---|
| siem-vm (Ubuntu Server) | 4 | **10 GB** | 60 GB | Wazuh indexer is a hungry JVM; give it room |
| victim-vm (Ubuntu Desktop) | 4 | **6 GB** | 50 GB | Desktop GUI + detonation headroom |
| kali-vm (Kali Linux) | 2 | **4 GB** | 40 GB | Mostly CLI attack tooling, doesn't need much |
| Host (Windows) | — | ~12 GB left | — | Comfortable; all three VMs run at once |

---

## Architecture

```
WINDOWS HOST — VMware Workstation, git, the GitHub repo, Claude Code runs here
   │
   └─ VMnet10  (host-only, ISOLATED: no NAT, no route to internet or your LAN)
        │
        ├─ siem-vm  (Ubuntu Server)          STABLE — pure defense, never attacks
        │    • Docker + Wazuh (indexer / manager / dashboard)
        │    • INetSim container = fake internet (DNS + HTTP sinkhole)
        │    • holds all logs, detection rules, and history
        │
        ├─ victim-vm (Ubuntu Desktop)        DISPOSABLE — snapshot before every run
        │    • Wazuh agent  → ships logs to siem-vm
        │    • auditd + Sysmon-for-Linux (telemetry)
        │    • Invoke-AtomicRedTeam (local atomics) + sample detonation area
        │    • its ONLY network path is VMnet10 (siem-vm + kali-vm)
        │
        └─ kali-vm (Kali Linux)              ATTACKER — the only offense-capable box
             • Metasploit / Nmap / C2 tooling, attacks victim-vm over VMnet10
             • second adapter (NAT) for tool updates only — IP forwarding
               disabled, so it can never bridge VMnet10 to the real internet
```

**Why three VMs:** the machine collecting evidence should not be the machine
getting compromised, and the machine doing the attacking shouldn't hold
defensive telemetry either. A sample that trashes the victim never costs you
your accumulated detection work, and keeping attack tooling off siem-vm and
victim-vm means neither one needs anything offensive installed on it.
**Why the repo lives on the host + GitHub:** it outlives every VM revert or
rebuild.

---

## Where the prompts go

Paste these into **Claude Code (the CLI) running on your Windows host**, in the empty
folder where the repo will live (e.g. `C:\dev\purple-lab`). Not into a VM, not into
the Claude web app. Claude Code authors the repo on the host and pushes to GitHub;
the VMs then `git clone` it and run the provisioning scripts inside themselves.

## How to use this chain

1. Run Claude Code **on your Windows host**, in the folder where the repo will live.
2. Feed the prompts **one at a time**, in order. Wait for each to finish, read what
   it produced, then run the manual step (if any), then move on.
3. **Commit after every prompt** (Prompt 1 sets up git; after that, commit + push
   before starting the next prompt). Small commits = a portfolio-grade history.
4. When a prompt says **[MANUAL]**, that's a step you do in the VMware GUI or inside
   a VM — Claude Code writes the runbook, but you click the buttons / run the script.
5. If a prompt is too big for one go, tell Claude Code "do step N only" — the repo's
   `CLAUDE.md` (created in Prompt 1) keeps it consistent across sessions.

> **Safety rule, always:** the victim VM must have **no route to the real internet**
> before you ever run an atomic or open a sample. Prompt 3 builds a script that
> verifies this; run it before every detonation. Snapshot clean, detonate, revert.

---

## Leaving it running unattended (auto-accept / "/rc on")

Be realistic about what an unattended Claude Code run can and can't do. The prompts
split into two kinds:

**Can run unattended (pure authoring — no VM needed):**
Prompts **0, 1, 5, 6, 7, 8, 9**. These write the repo, docs, runbook, the Python CLI,
the Sigma pipeline, CI, the coverage dashboard, and the detonation *workflow code*.
None of them need a VM to exist. You can safely queue these and step away.

**CANNOT run unattended (need the VMs to exist + interactive verification):**
Prompts **2, 3, 4, 4B** run *inside* siem-vm, victim-vm, and kali-vm and check
things like "did the Wazuh dashboard load", "does the containment check fail
closed", "did the agent connect", "is kali-vm's IP forwarding actually off". The
VMs don't exist until you build them by hand (the `[MANUAL]` step after Prompt 1),
and these steps need your eyes on the result. **Do not** let an unattended agent
decide containment is fine — you verify that one yourself, every time.

### So the sane hand-off plan

1. **You, present:** run Prompts 0 and 1. Read the VM build runbook it produces.
2. **You, present:** do the `[MANUAL]` VMware step — build VMnet10 + all three
   VMs, clone the repo inside each, take base snapshots. (~1–1.5 hours, one time.)
3. **Unattended is fine here:** while you're doing the VM build, or overnight, let
   Claude Code run Prompts **5–9** to build all the tooling against the repo. Queue
   them with a note like: *"Do prompts 5 through 9 from docs/prompt-chain in order,
   committing after each. Skip anything that requires a running VM and leave me a
   TODO note instead."*
4. **You, present, later:** run Prompts 2, 3, 4, 4B inside the VMs and verify each
   (dashboard loads, containment fails closed, agent connects, kali-vm forwarding
   is off).

That way the boring code-authoring happens while you're away, and the safety-
critical VM steps stay under your eye.

### Before you walk away — pre-flight checklist

Set these up so an unattended run doesn't stall on a missing credential or a
permission prompt:

- [ ] Claude Code installed and working on the Windows host, opened in the repo folder
- [ ] `git` configured (name + email) and `gh` authenticated (`gh auth status` is green)
- [ ] The GitHub repo created and set as the remote (do Prompt 0 while present)
- [ ] `docs/prompt-chain.md` (this file) saved **inside the repo** so Claude Code can read it
- [ ] Auto-accept / "/rc" mode on, with a clear queued instruction naming which
      prompts to run and to **skip VM-dependent steps** (2/3/4) and leave TODOs
- [ ] Python + pipx available on the host (the CLI in Prompts 5–7 gets built/tested here)
- [ ] No secrets needed yet — Wazuh API creds only matter in Prompts 5–8, and those
      are read from a gitignored `.env` you fill in later, so the run won't block on them

> Reality check: the fastest safe path is **you present for Prompts 0–1 and the VM
> build, unattended for 5–9, you present again for 2–4.** The lab can't fully build
> itself while you sleep — the VMs and the containment check need a human.

---

## The prompt chain

### Prompt 0 — Repo + GitHub

```
I'm building a contained purple-team home lab and I want this folder to be a
public GitHub portfolio repo. Initialize a git repository here, create a sensible
.gitignore for Python + Docker + secrets, and a LICENSE (MIT). Create an initial
README stub titled "Purple Lab" with a one-paragraph description: a two-VM,
network-isolated detection-engineering lab where I run Atomic Red Team techniques
and real malware samples against an Ubuntu victim VM, collect telemetry in Wazuh,
and write Sigma detections in a daily loop. Then walk me through creating the repo
on GitHub and pushing (give me the exact gh/git commands). Do not add any secrets.
```

*After this: create the GitHub repo and push.*

---

### Prompt 1 — Scaffold, docs, and the VMware build runbook  **[MANUAL follows]**

```
Scaffold the full project. Create this structure with placeholder files and a
CLAUDE.md that documents our conventions (Python for tooling, Docker Compose for
Wazuh, bash for provisioning, Sigma for detections, everything idempotent):

  /docs        ARCHITECTURE.md, VM-BUILD-RUNBOOK.md, CONTAINMENT-AND-SAFETY.md
  /provision   siem/, victim/, and kali/ setup scripts (stubs for now)
  /tooling     the Python "purplelab" CLI package (stub)
  /detections  Sigma rules live here (empty + a README)
  /journal     daily-loop log lives here (empty + a README)
  /samples     .gitignored — real malware never gets committed

Write ARCHITECTURE.md fully: the three-VM design above (siem-vm = Ubuntu Server
with Wazuh + INetSim; victim-vm = Ubuntu with Wazuh agent, auditd,
Sysmon-for-Linux, Invoke-AtomicRedTeam; kali-vm = the only attacker box, dual
NIC), the isolated VMnet10 network with no NAT (except kali-vm's second, NAT'd
adapter for tool updates only, with IP forwarding verified off), and why the
repo lives on the host.

Write VM-BUILD-RUNBOOK.md as an exact step-by-step for VMware Workstation on
Windows: creating VMnet10 as a host-only network with NAT disabled in the Virtual
Network Editor; creating all three VMs (specs, ISO, adapter settings so victim-vm
is ONLY on VMnet10, and kali-vm gets a second NAT adapter for tool updates with
IP forwarding verified off); enabling nested settings if needed; and taking a
clean base snapshot of each. Be specific about which adapter(s) each VM gets.

Write CONTAINMENT-AND-SAFETY.md: the rules for handling real samples (snapshot
before, revert after, verify no egress, never mount host shares on the victim
during detonation, never put credentials on the victim, and never let kali-vm
bridge its NAT adapter to VMnet10).
```

**[MANUAL]** Follow `VM-BUILD-RUNBOOK.md`: install VMware if needed, create VMnet10,
build **siem-vm**, **victim-vm**, and **kali-vm**, set their network adapters
(kali-vm gets two, verify IP forwarding is off), `git clone` your repo inside
each VM, and take a **clean base snapshot** of each.

---

### Prompt 2 — SIEM box provisioning (Wazuh)  **[run inside siem-vm]**

```
Write /provision/siem/install.sh: an idempotent bash script that provisions the
siem-vm (Ubuntu Server). It should install Docker + Docker Compose, then stand up
a single-node Wazuh stack (indexer + manager + dashboard) via docker compose,
pinned to a specific Wazuh version, with volumes so data persists. Generate the
compose file at /provision/siem/docker-compose.yml. Include a Makefile with
targets: `make siem-up`, `make siem-down`, `make siem-logs`, `make siem-status`.
After it's up, print the dashboard URL and how to retrieve the admin password.
Add a /provision/siem/README.md explaining how to run it inside siem-vm and how
to reach the dashboard from the host browser over VMnet10.
```

**[MANUAL]** In siem-vm: `git pull`, run `make siem-up`, confirm the Wazuh dashboard
loads from your host browser. Snapshot siem-vm as "wazuh-installed".

---

### Prompt 3 — Fake-internet containment + egress verifier  **[run inside siem-vm]**

```
On the siem-vm I want a fake-internet sinkhole for detonating samples safely.
Add an INetSim service to the SIEM docker-compose (or a dedicated compose in
/provision/siem/inetsim/) configured to answer DNS and HTTP/HTTPS for any request
with canned responses, logging everything. Document how the victim-vm points its
DNS and default route at the siem-vm's VMnet10 IP so the sample's C2 traffic hits
the sinkhole and nothing leaves.

Then write /tooling scripts + a `purplelab containment-check` command that I run
FROM the victim-vm before any detonation: it must actively verify there is NO real
internet egress (fail if it can reach an external IP/domain), confirm DNS resolves
to the sinkhole, confirm the Wazuh agent is connected, and (via SSH to kali-vm, or
a small status endpoint there) confirm kali-vm's IP forwarding is off and no
bridging NAT rule exists — kali-vm's NAT adapter is the one real-internet path in
the lab, so this check verifies it rather than trusting it stayed off. It should
exit non-zero and print a loud warning if containment is not intact. Make this
the mandatory pre-flight gate.
```

**[MANUAL]** Bring up INetSim, run the containment check from victim-vm — it must
**fail closed** if the victim can reach the real internet. Fix networking until the
check passes. Snapshot siem-vm as "containment-ready".

---

### Prompt 4 — Victim box provisioning (telemetry + attack tooling)  **[run inside victim-vm]**

```
Write /provision/victim/install.sh: an idempotent bash script for the victim-vm
(Ubuntu). It should:
  1. Install and enroll the Wazuh agent, pointing at the siem-vm manager IP, and
     confirm it shows up in the Wazuh dashboard.
  2. Install auditd and deploy a strong audit ruleset (base it on a well-known
     Linux auditd ruleset covering execve, file, network, and persistence events)
     to /provision/victim/audit.rules.
  3. Install Sysmon-for-Linux with a sensible config at
     /provision/victim/sysmon-config.xml, and verify events flow.
  4. Install PowerShell (pwsh) and Invoke-AtomicRedTeam + the atomics folder, so I
     can run Linux-tagged Atomic Red Team tests by technique ID.
  5. Create a locked-down /samples working dir for detonation (gitignored, correct
     perms) and print safety reminders.
Add a /provision/victim/README.md and Makefile targets: `make victim-provision`,
`make victim-verify` (checks agent connected + auditd + sysmon + pwsh + atomics).
```

**[MANUAL]** In victim-vm: `git pull`, run `make victim-provision`, then
`make victim-verify`. Run one command and confirm it appears in the Wazuh
dashboard within seconds. Snapshot victim-vm as **"clean-baseline"** — this is the
snapshot you revert to before every run.

---

### Prompt 4B — Kali attacker box provisioning  **[run inside kali-vm]**

```
Write /provision/kali/install.sh: an idempotent bash script for kali-vm. It
should:
  1. Update apt and confirm core attack tooling is present (Metasploit
     Framework, Nmap, and whatever else a stock Kali install already ships
     with) — this script is about verifying/updating what's there and
     documenting it, not building a custom toolset from scratch.
  2. Verify and enforce the safety-critical network posture: confirm exactly
     two interfaces (one on VMnet10, one NAT), confirm IP forwarding is
     disabled (net.ipv4.ip_forward and net.ipv6.conf.all.forwarding both 0,
     persisted via /etc/sysctl.d/ so it survives reboot), and confirm no
     NAT/masquerade rule bridges the two interfaces (iptables -t nat -L -n -v).
     Fail loudly and refuse to continue if any of this doesn't hold.
  3. `git clone`/pull this repo if not already present, and print the
     siem-vm and victim-vm IPs it expects (from a small config file, not
     hardcoded).
Add /provision/kali/README.md explaining how to run it inside kali-vm and how it
relates to the containment check that victim-vm runs before detonation. Add a
Makefile target `make kali-verify` that re-runs just the network posture checks
from step 2, so I can re-verify kali-vm's isolation any time without
re-provisioning tools.
```

**[MANUAL]** In kali-vm: `git pull`, run `provision/kali/install.sh`, then
`make kali-verify`. Confirm the output shows IP forwarding off and no bridging
NAT rule. From kali-vm, confirm you can reach victim-vm and siem-vm over VMnet10
**and** the real internet over the NAT adapter. Snapshot kali-vm as
**"tooling-ready"**.

---

### Prompt 5 — The daily-loop CLI (`purplelab`)

```
Build the Python "purplelab" CLI in /tooling as a proper package (pyproject.toml,
installable with pipx). Commands:

  purplelab pick [--tactic X]   suggest an ATT&CK technique I haven't covered yet,
                                using my journal + a list of available Linux atomics
  purplelab run <T-id>          remind me to snapshot victim-vm, then either run the
                                matching Atomic Red Team test locally via pwsh, or
                                (for techniques better represented as a remote
                                attack) print the staged kali-vm command to run by
                                hand, and record start time either way
  purplelab check <T-id>        query the Wazuh API (indexer) for events/alerts in
                                the time window since `run`, and report: did anything
                                fire? what raw telemetry exists? time-to-detect?
  purplelab log <T-id>          interactive: record technique, whether it was caught
                                blind, which Sigma rule (if any) I wrote, notes, and
                                time-to-detect, appended to /journal as JSON + a
                                human-readable markdown log
  purplelab today               show my streak, recent entries, and what to do next

Store Wazuh API creds via env vars / a .env that is gitignored — never hardcode.
Include a config file for the siem-vm IP and API details. Write tests for the
journal + coverage logic.
```

---

### Prompt 6 — Sigma detection pipeline + tests + CI

```
Set up the detection-engineering pipeline in /detections. Use pySigma / sigma-cli
to convert my Sigma rules into Wazuh-compatible rules and deploy them to the
manager. Provide:
  - a directory convention: /detections/<tactic>/<technique>.yml
  - `purplelab sigma convert` and `purplelab sigma deploy` commands
  - a detection TEST HARNESS: for a given technique, revert reminder → run the
    atomic → assert the corresponding alert fires in Wazuh (a real detection unit
    test), and report pass/fail
  - a GitHub Actions workflow that validates all Sigma rule syntax on every push
    (no VM needed for CI — just lint/convert), with a status badge for the README
Seed /detections with ONE working example rule for a simple technique (e.g. a
suspicious cron persistence or base64-decoded shell execution) end to end.
```

---

### Prompt 7 — ATT&CK coverage dashboard

```
Add `purplelab coverage`: read my /detections rules + /journal and generate
  1. an ATT&CK Navigator layer JSON (techniques I have detections for = scored/
     colored), which I can load into the Navigator to see my coverage map, and
  2. a self-contained HTML coverage report (no external dependencies, works in a
     browser, light + dark friendly) showing coverage % by tactic, my streak,
     time-to-detect trend, and gaps to work on next.
Regenerate both on demand. Explain how to load the layer in ATT&CK Navigator.
```

---

### Prompt 8 — Real-sample detonation workflow (safety-gated)

```
Build the guided real-sample workflow as `purplelab detonate`. It must enforce the
safety sequence and refuse to proceed if any gate fails:
  1. confirm I'm on the victim-vm and it's reverted to the clean-baseline snapshot
  2. run the containment-check (Prompt 3) — abort if egress is possible
  3. record the sample hash, capture a clean telemetry baseline
  4. detonate in /samples, collect auditd + Sysmon + Wazuh telemetry + INetSim logs
     (the C2 beacons hitting the sinkhole) for a fixed window
  5. bundle the collected telemetry into /journal as an evidence folder
  6. remind me to REVERT the snapshot, and prompt me to turn the observed behavior
     into a new Sigma rule
Document a safe source for samples (MalwareBazaar / theZoo) and the handling rules
from CONTAINMENT-AND-SAFETY.md. Never commit samples; keep /samples gitignored.
```

---

### Prompt 9 — One-command lab + portfolio polish

```
Make this a daily driver and a strong portfolio piece:
  - a top-level Makefile / justfile: `make lab-up` (bring up siem services),
    `make lab-down`, `make daily` (runs `purplelab today`)
  - finish the README: architecture diagram, the daily-loop explanation, a quickstart,
    the CI badge, a coverage screenshot placeholder, and a clear "this is a contained
    lab — do not run against systems you don't own" safety note
  - a CONTRIBUTING/roadmap section listing future work (CALDERA automation, Windows
    victim VM, auto-run a random atomic each morning and diff alerts)
  - review the whole repo for leaked secrets or committed samples before I make it public
Then give me the commands to push and flip the repo to public.
```

---

## The daily ritual once it's built

1. `purplelab today` — see your streak and what to tackle.
2. Revert victim-vm to **clean-baseline**.
3. `purplelab pick` → `purplelab run <T-id>`.
4. `purplelab check <T-id>` — did it fire? If not, why?
5. Write/fix a Sigma rule in `/detections`, `purplelab sigma deploy`, re-run, confirm it fires.
6. `purplelab log <T-id>`, commit, push.

Fifteen minutes. Every entry is one ATT&CK technique you now understand from both sides.

---

## Order of operations recap

| Step | Where | What |
|---|---|---|
| Prompt 0–1 | Host (Claude Code) | Repo, docs, VM build runbook |
| **[MANUAL]** | VMware | Build VMnet10 + all three VMs, base snapshots, clone repo in each |
| Prompt 2 | Claude Code → run in siem-vm | Wazuh up |
| Prompt 3 | Claude Code → run in siem-vm + victim-vm | Fake-internet + containment gate |
| Prompt 4 | Claude Code → run in victim-vm | Telemetry + attack tooling, clean-baseline snapshot |
| Prompt 4B | Claude Code → run in kali-vm | Attack tooling + verified network isolation, tooling-ready snapshot |
| Prompt 5–7 | Host (Claude Code) | CLI, Sigma pipeline + CI, coverage dashboard |
| Prompt 8 | Claude Code | Safety-gated real-sample workflow |
| Prompt 9 | Claude Code | One-command lab + go public |

Build the lab first (Prompts 0–4B), then the tooling grows around a working loop.
