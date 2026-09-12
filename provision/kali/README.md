# provision/kali

Provisioning for **kali-vm**, the lab's only attacker box. Unlike
`provision/siem` and `provision/victim`, this isn't installing a toolset from
scratch -- stock Kali already ships with Metasploit, Nmap, and the rest.
What actually matters here is **network posture**: kali-vm is the one VM
with a real-internet-facing adapter (NAT, for tool updates only), and that's
only safe as long as it never routes traffic between that adapter and its
VMnet10 adapter. See `docs/CONTAINMENT-AND-SAFETY.md` rule 8 and
`docs/ARCHITECTURE.md`.

Run this inside `kali-vm`, after cloning the repo there:

```
make kali-provision   # tooling check + network posture (install.sh)
make kali-verify       # JUST the network posture check, any time
```

`verify-network.sh` (called by both targets) checks and enforces:

- Exactly 2 network adapters (VMnet10 + NAT) -- fails if not.
- `net.ipv4.ip_forward` and `net.ipv6.conf.all.forwarding` are `0`, set now
  and persisted via `/etc/sysctl.d/99-vanta-no-forward.conf` so it survives
  reboots, not just the current session.
- No `MASQUERADE` rule in `iptables -t nat` that could bridge the two
  interfaces.

**It fails loudly and exits non-zero on any bad posture** -- it never
continues past something it can't confirm. This is the same fail-closed
philosophy as `purplelab containment-check` (`tooling/`), which re-verifies
this same posture remotely from the host before any detonation
(`check_kali_no_bridging` in `tooling/purplelab/containment.py`) -- run
`kali-verify` here on kali-vm itself any time you change its network config,
and let `purplelab containment-check` be the gate that actually blocks a
detonation.

`install.sh` also prints the siem-vm/victim-vm IPs it expects, read from
`tooling/config.yaml` (never hardcoded) -- fill that in on the host and
`git pull` it here once it's set.
