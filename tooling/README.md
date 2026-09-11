# tooling — the `purplelab` CLI

The Python package that drives the daily loop from the Windows host: pick a
technique, run it against victim-vm, check Wazuh for detections, log the
result, manage the Sigma pipeline, generate coverage reports, and gate
real-sample detonation behind containment checks.

**Status:**

- **Prompt 5 (done)** — `pick`, `run`, `check`, `log`, `today`. Journal and
  technique-catalog logic covered by tests (`tests/test_journal.py`,
  `tests/test_atomics.py`); `run`/`check` need live victim-vm/siem-vm to
  actually do anything beyond print instructions.
- **Prompt 6 (done)** — `sigma convert`, `sigma deploy`, `sigma test` (the
  detection test harness). `convert` works fully offline (covered by
  `tests/test_sigma_pipeline.py`, and run by CI on every push); `deploy`/`test`
  need a live Wazuh indexer.
- **Prompt 7 (done)** — `coverage`: writes `coverage/navigator-layer.json`
  (ATT&CK Navigator layer) and `coverage/report.html` (self-contained, works
  offline, light/dark aware) from `detections/` + `journal/`. Both files are
  generated, gitignored, and regenerated on demand -- covered by
  `tests/test_coverage.py`.
- **Prompt 8** — `containment-check`, `detonate`

## Install

```
pip install -e ".[dev]"        # from tooling/, inside a venv
```

(`pipx install -e tooling/` also works once you want `purplelab` on PATH
without activating a venv.)

## Config

- `tooling/config.yaml` — non-secret settings: siem-vm IP, victim agent name,
  optional victim-vm SSH host/user (for `run` to execute atomics remotely
  instead of just printing the command).
- `tooling/.env` (gitignored, copy from `.env.example`) — Wazuh API
  credentials. Never hardcoded, never committed.

## Test

```
pytest -q
```

Tests that need live infra (Wazuh, victim-vm) aren't run here — only the pure
logic (journal, technique catalog, Sigma parsing/conversion) is.
