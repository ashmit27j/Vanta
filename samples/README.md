# samples

Working directory for real malware sample detonation. **Gitignored — nothing in
here except this README and `.gitkeep` is ever committed.**

See `docs/CONTAINMENT-AND-SAFETY.md` before putting anything here:

- Samples are pulled from MalwareBazaar or theZoo, downloaded directly onto
  **victim-vm**, never onto the host or siem-vm.
- Record each sample's SHA256 hash in the journal entry before detonating.
- Detonation only happens through `purplelab detonate` (Prompt 8) once it
  exists, which gates on a clean-snapshot revert and a passing containment
  check.
