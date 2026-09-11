# journal

The daily-loop history: one entry per technique run, recording whether it was
caught blind, which Sigma rule (if any) was written or fixed, notes, and
time-to-detect.

**Status:** empty. Prompt 5 adds `purplelab log <T-id>`, which appends entries
here as JSON (machine-readable, used by `purplelab pick`/`coverage`/`today`) and
as human-readable markdown.

Real-sample detonation evidence bundles (Prompt 8) land under
`journal/evidence/`, which is gitignored — telemetry captures can be large and
are tied to specific local runs, not meant to be committed.
