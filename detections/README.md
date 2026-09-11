# detections

Sigma detection rules, one technique per file.

## Convention

```
detections/<tactic>/<technique>.yml
```

- `<tactic>` — the ATT&CK tactic slug, e.g. `persistence`, `execution`,
  `defense-evasion`.
- `<technique>` — the ATT&CK technique ID, e.g. `T1053.003` (cron), `T1059.004`
  (unix shell). The filename stem is also the ID `purplelab` uses to associate
  a rule with a technique.

## Pipeline

- `purplelab sigma convert [path]` — parse and validate rule(s) (or all of
  them, if no path given) and print the Lucene query pySigma converts them to.
  This is also what CI runs on every push (`.github/workflows/ci.yml`) to
  catch broken Sigma syntax before merge.
- `purplelab sigma deploy [path]` — convert and deploy as an OpenSearch
  Alerting monitor on siem-vm's Wazuh indexer (idempotent: updates the
  existing monitor if one already exists for that technique).
- `purplelab sigma test <T-id>` — the detection test harness: reminds you to
  revert victim-vm, runs the technique, waits for you to confirm it's done,
  then asserts the deployed monitor produced a finding in that window.
  Pass/fail, not just "did an alert print somewhere."

Two things to verify once siem-vm is actually live (see
`tooling/purplelab/sigma_pipeline.py` docstring for detail):

1. **Field mapping.** Rules are written using Sigma's generic
   `process_creation` taxonomy (`Image`, `CommandLine`, ...); these get
   mapped to Wazuh's decoded Sysmon-for-Linux field names
   (`data.win.eventdata.*`) before conversion. That mapping is a best-effort
   placeholder until checked against a real decoded event.
2. **Archives.** Monitors query `wazuh-archives-*`, which requires archives
   enabled on the Wazuh manager (`logall_json: yes`) — otherwise there's
   nothing to query for activity Wazuh's own rules haven't already alerted
   on, which defeats the point of writing a new detection.

## Seed rule

`persistence/T1053.003.yml` — cron persistence via the `crontab` command,
working end to end through `sigma convert` (verified locally; `deploy`/`test`
need live siem-vm).
