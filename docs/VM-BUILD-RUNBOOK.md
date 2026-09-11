# VM Build Runbook (VMware Workstation on Windows)

Follow this once, in order, to stand up the isolated lab network and both VMs.
This is a **[MANUAL]** step — do it yourself in the VMware Workstation GUI; no
script does this for you, because getting the network isolation right needs your
eyes on it.

Prerequisites:

- VMware Workstation Pro (or Player) installed on the Windows host.
- An Ubuntu Server ISO (for siem-vm) and an Ubuntu Desktop ISO (for victim-vm).
  Use a current LTS release for both.
- ~32GB host RAM, ~110GB free disk for both VMs combined.

---

## 1. Create the isolated network: VMnet10

This is the step that makes the whole lab safe. Get it right before creating
either VM.

1. Open VMware Workstation.
2. Go to **Edit → Virtual Network Editor**.
3. Click **Change Settings** (admin elevation required on Windows).
4. Click **Add Network...**, choose **VMnet10** (or the next free custom VMnet if
   10 is taken — just be consistent below), click OK.
5. With VMnet10 selected, set its type to **Host-only**.
6. **Uncheck "Use local DHCP service to distribute IP address to VMs"** — you want
   explicit static IPs later (or a controlled DHCP range you fully understand),
   not a default that could quietly relax later. If you'd rather use DHCP for
   convenience, that's fine too — just confirm it only serves VMnet10.
7. Confirm **"Connect a host virtual adapter to this network"** is checked — this
   is what lets your Windows host browser reach the Wazuh dashboard.
8. Set the subnet, e.g. `192.168.110.0` / `255.255.255.0` (pick anything that
   doesn't collide with your real LAN).
9. Critically: **VMnet10 must NOT be a NAT network.** Do not check "Use local DHCP
   service" tied to a NAT type, and do not add a NAT device to this VMnet. Host-only
   with no NAT means: no route out to your LAN, no route out to the internet.
10. Click **Apply**, then **OK**.

Verify: back in the Virtual Network Editor summary list, VMnet10 should show
**Type: Host-only**, with no NAT column entry.

---

## 2. Create siem-vm (Ubuntu Server)

1. **File → New Virtual Machine → Custom (advanced)**.
2. Hardware compatibility: latest supported by your VMware version.
3. **Installer disc image (ISO)**: point at your Ubuntu Server ISO.
4. Guest OS: Linux, version Ubuntu 64-bit.
5. VM name: `siem-vm`. Location: wherever you keep VMs (not inside the repo).
6. **Processors**: 4 vCPU (1 socket × 4 cores, or 2×2 — either is fine).
7. **Memory**: 12 GB (12288 MB).
8. **Network type**: choose **"Use a custom network adapter"** → select
   **VMnet10**. Do **not** leave it on NAT or Bridged.
9. I/O controller / disk type: defaults are fine (NVMe or SCSI, whichever your
   VMware version recommends).
10. **Disk**: 60 GB, "Store virtual disk as a single file" is simplest.
11. Finish. Before first boot, open **Edit virtual machine settings**:
    - **Network Adapter**: confirm it shows **Custom: VMnet10**.
    - **Processors**: confirm **"Virtualize Intel VT-x/EPT or AMD-V/RVI"** is
      enabled if you plan to run nested containers heavily (Docker doesn't
      strictly require this, but it helps performance) — this is under
      Processors → the virtualization engine checkbox.
12. Boot the VM, install Ubuntu Server normally (username/password of your
    choice — this box never touches your real accounts). During install, when
    asked about networking, DHCP is fine (VMnet10's own DHCP, if you enabled it
    in step 1) or set a static IP in the `192.168.110.0/24` range you chose.
13. After install completes and you've logged in once, note siem-vm's IP
    (`ip a`) — victim-vm's provisioning will need it.
14. `git clone` this repo inside siem-vm (install `git` first: `sudo apt install
    -y git`).

---

## 3. Create victim-vm (Ubuntu Desktop)

1. **File → New Virtual Machine → Custom (advanced)**, same wizard as above.
2. **Installer disc image (ISO)**: your Ubuntu Desktop ISO.
3. Guest OS: Linux, Ubuntu 64-bit.
4. VM name: `victim-vm`.
5. **Processors**: 4 vCPU.
6. **Memory**: 8 GB (8192 MB).
7. **Network type**: **"Use a custom network adapter"** → **VMnet10**. This is
   the single most important setting on this VM — **victim-vm must have exactly
   one network adapter, and it must be VMnet10.** Do not add a second adapter
   (no NAT, no Bridged, no second host-only network). If the New VM wizard added
   a default adapter, remove it and add only the VMnet10 one.
8. **Disk**: 50 GB.
9. Finish. Before first boot, open **Edit virtual machine settings** and verify:
    - Exactly **one** Network Adapter, type **Custom: VMnet10**.
    - Processors: virtualization passthrough enabled (same as siem-vm, optional
      but helps if you run containers here too).
10. Boot and install Ubuntu Desktop normally.
11. After install, verify from a terminal in victim-vm that you can reach
    siem-vm's IP but nothing else (`ping <siem-vm-ip>` should work; `ping
    8.8.8.8` or any real external IP should **hang/fail** — if it succeeds, stop
    and fix the network adapter before going further).
12. `sudo apt install -y git`, then `git clone` this repo inside victim-vm.

---

## 4. Base snapshots

Snapshot **both** VMs once provisioning-from-ISO is done and the repo is cloned,
before running any provisioning scripts. This is your fallback if a later step
goes wrong.

In VMware Workstation, with each VM selected:

- **VM → Snapshot → Take Snapshot...**
- Name it `base-install` for both `siem-vm` and `victim-vm`.
- Description: note the date and Ubuntu version installed.

You'll take further snapshots later in the prompt chain (`wazuh-installed`,
`containment-ready` on siem-vm; `clean-baseline` on victim-vm) — `base-install` is
just the "ISO installed, repo cloned, nothing else done yet" checkpoint.

---

## 5. Sanity checks before moving on

Run these before starting Prompt 2:

- [ ] VMnet10 in the Virtual Network Editor shows Host-only, no NAT.
- [ ] siem-vm has one adapter, on VMnet10; you can reach its dashboard port range
      later from the Windows host.
- [ ] victim-vm has **exactly one** adapter, on VMnet10, and cannot reach any real
      external IP (verified with `ping` above).
- [ ] Both VMs can reach each other over VMnet10 (`ping` each other's IP).
- [ ] Both VMs have this repo cloned via `git clone`.
- [ ] `base-install` snapshot exists for both VMs.

Once all of that holds, move on to Prompt 2 (siem-vm provisioning).
