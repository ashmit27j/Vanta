# tooling — the `purplelab` CLI

The Python package that drives the daily loop from the Windows host: pick a
technique, run it on victim-vm, check Wazuh for detections, log the result,
manage the Sigma pipeline, generate coverage reports, and gate real-sample
detonation behind containment checks.

**Status:** stub package (`pyproject.toml`, `purplelab/cli.py`). Commands are
built out by:

- **Prompt 5** — `pick`, `run`, `check`, `log`, `today`
- **Prompt 6** — `sigma convert`, `sigma deploy`, detection test harness
- **Prompt 7** — `coverage`
- **Prompt 8** — `containment-check`, `detonate`

Install locally (once implemented) with `pipx install -e tooling/` from the repo
root, or `pip install -e tooling/` inside a venv for development.

Wazuh API credentials and the siem-vm IP are read from a gitignored `.env` /
config file — never hardcoded. See `.env.example` once Prompt 5 adds it.
