# detections

Sigma detection rules, one technique per file.

## Convention

```
detections/<tactic>/<technique>.yml
```

- `<tactic>` — the ATT&CK tactic slug, e.g. `persistence`, `execution`,
  `defense-evasion`.
- `<technique>` — the ATT&CK technique ID, e.g. `T1053.003` (cron), `T1059.004`
  (unix shell).

**Status:** empty. Prompt 6 sets up the conversion/deploy pipeline
(`purplelab sigma convert` / `purplelab sigma deploy`, pySigma/sigma-cli targeting
Wazuh, a detection test harness, and CI rule-syntax validation) and seeds one
working end-to-end example rule here.
