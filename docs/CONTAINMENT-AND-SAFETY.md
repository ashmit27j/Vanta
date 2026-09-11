# Containment & Safety

This lab is designed so real malware samples can be detonated safely. That
safety comes entirely from discipline: the network isolation described in
`ARCHITECTURE.md` and `VM-BUILD-RUNBOOK.md` only holds if these rules are
followed every single time, not most of the time.

## The non-negotiable rules

1. **Snapshot victim-vm clean before every run.**
   Before running an Atomic Red Team test, and *always* before detonating a real
   sample, victim-vm must be reverted to its `clean-baseline` snapshot (or, for
   very early testing, `base-install`). Never build on top of a previous run's
   leftover state — persistence mechanisms, dropped files, or modified configs
   from a prior technique can mask or corrupt what you observe next.

2. **Revert victim-vm after every run.**
   Once you've collected telemetry and logged the result, revert immediately.
   Don't leave a detonated VM running "for later" — it's now untrusted.

3. **Verify no egress before every detonation.**
   Run the containment check (`purplelab containment-check`, built in Prompt 3)
   immediately before opening or executing any sample or atomic that could reach
   out to a network. It must confirm:
   - No route to a real external IP/domain exists.
   - DNS resolves to the INetSim sinkhole on siem-vm, not a real resolver.
   - The Wazuh agent is connected (so whatever happens is actually observed).
   If any of these checks fail, **do not proceed.** Fix the network first.

4. **Fail closed, always.**
   Any tooling in this repo that reasons about containment (the containment
   check, the detonation workflow) must treat an *inconclusive* result as unsafe.
   If a check can't positively confirm isolation, it reports failure — it never
   assumes "probably fine." This applies to code you write here as much as to
   your own manual judgment.

5. **Never commit real samples.**
   `samples/` is gitignored for exactly this reason. Don't work around it, don't
   add per-file exceptions, don't zip samples into something that dodges
   `.gitignore`. Malware samples never enter git history — once something is
   committed, `git filter-repo`/history rewrite is the only way out, and public
   repos may already have been scraped by then.

6. **Never mount host shares on victim-vm during detonation.**
   No VMware shared folders, no drag-and-drop, no clipboard sharing enabled while
   a sample might be running. A sample that escapes the guest OS (privilege
   escalation, hypervisor exploit, or just a helpfully-mounted host drive) should
   not find a path back to your host filesystem. Keep shared folders **disabled**
   on victim-vm as a standing setting, not something you remember to turn off.

7. **Never put real credentials on victim-vm.**
   No saved browser logins, no SSH keys to other machines, no cloud CLI sessions,
   no password manager. Anything on victim-vm should be assumed to eventually
   leak to whatever you detonate there. Use a throwaway local user/password
   created during Ubuntu install and nothing else.

## Where samples come from

When you're ready to work with real samples (Prompt 8), pull them from sources
built for this purpose, not from opportunistic browsing:

- **[MalwareBazaar](https://bazaar.abuse.ch/)** (abuse.ch) — curated, hash-indexed
  samples with family tags; requires acknowledging research/defensive use.
- **[theZoo](https://github.com/ytisf/theZoo)** — a maintained repo of live
  malware samples for research, with clear usage guidelines.

Handling rules for anything pulled from either source:

- Download directly into victim-vm's locked-down `/samples`-equivalent working
  directory — never onto the host, never onto siem-vm.
- Record the sample's hash (SHA256) in the journal entry before detonating, so
  the evidence bundle is tied to a specific known sample.
- Treat the archive password (both sources ship samples zip-password-protected,
  typically `infected`) as a safety feature, not friction — it exists so samples
  aren't accidentally executed by AV/indexing/preview tools before you're ready.

## What the detonation workflow enforces in code

Prompt 8 builds `purplelab detonate` to encode rules 1–4 above as actual gates,
not just documentation: it will refuse to proceed if victim-vm isn't confirmed
reverted, if the containment check fails, or if any step in the sequence can't be
verified. Treat that command as the single sanctioned way to run a real sample in
this lab — don't detonate samples by hand outside of it once it exists.
