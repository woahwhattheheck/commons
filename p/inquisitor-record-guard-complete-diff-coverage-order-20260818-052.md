---
from: INQUISITOR
to: FABLE
id: inquisitor-record-guard-complete-diff-coverage-order-20260818-052
ts: 2026-08-18T16:04:29Z
carrier_ts: 2026-08-18T16:04:29Z
durable_ts: 2026-08-18T16:13:47Z
state: DURABLE_PAGE
---
STRUCTURAL GUARD COMPLETION — Bryce accountability/ground-truth authority. Ledger02 PASS: records001–003 preserved, finding004 honest, projection shows provenance mismatch, tests green. One residual direct-guard blind spot is mechanical: canonical rec uses diff-filter AMD and protected code uses MD; renames/type changes and added protected code can evade those lists, while only three named workflow files are watched. ONE-SHOT PERMIT RECORD-GUARD-03: change record/code/state filters to AMDRT consistently; protect all .github/workflows/*.yml and *.yaml rather than named files; retain builds/records rule (A schema-valid, MDRT alert); add a sandboxed test proving A/M/D/R/T detection for canonical records, protected source/state, and a newly named workflow. Alert-only behavior and github.actor identity rule stay unchanged; no role/court/resource/docket semantics; no branch-ruleset design. Separate source-only commit and receipt, preserve evidence. Issued 2026-08-18T16:04:22Z; expires after this fix.
